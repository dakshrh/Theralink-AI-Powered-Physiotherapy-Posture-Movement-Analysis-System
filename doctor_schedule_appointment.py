import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import sqlite3
from datetime import datetime, date
import pandas as pd

# Register the page
dash.register_page(__name__, path='/doctor_schedule_appointment', title='Schedule Appointment', order=3)

DATABASE_PATH = 'theralink.db'

# Utility to get doctor_id from username (if needed, but we'll use user-id-store directly)
def get_doctor_id_from_username(username):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND role = 'doctor'", (username,))
    doctor_id = cursor.fetchone()
    conn.close()
    return doctor_id[0] if doctor_id else None

# Utility to get patient_id and name for dropdown
def get_all_patients_for_dropdown(doctor_id):
    conn = sqlite3.connect(DATABASE_PATH)
    # Fetch patients assigned to this doctor
    # If a doctor can schedule for ANY patient, remove the WHERE p.doctor_id = ? clause
    patients_df = pd.read_sql_query(f"""
        SELECT p.patient_id, p.name, u.username
        FROM patients p
        JOIN users u ON p.patient_id = u.id
        WHERE p.doctor_id = {doctor_id}
    """, conn)
    conn.close()
    
    options = []
    if not patients_df.empty:
        options = [{'label': f"{row['name']} ({row['username']})", 'value': row['patient_id']}
                   for index, row in patients_df.iterrows()]
    return options

# --- Layout for Doctor Schedule Appointment Page ---
def layout():
    # The actual patient options will be loaded by a callback after doctor_id is available
    return dbc.Container([
        dcc.Store(id='doctor-id-store-schedule-app', storage_type='session'),
        html.H2(id="schedule-app-header", className="text-center text-primary my-4"),
        dbc.Row(justify="center", children=[
            dbc.Col(md=8, lg=6, children=[
                dbc.Card([
                    dbc.CardHeader(html.H4("New Appointment", className="text-center")),
                    dbc.CardBody([
                        html.Div([
                            dbc.Label("Select Patient:", html_for="appointment-patient-select", className="fw-bold mb-2"),
                            dbc.Select(
                                id="appointment-patient-select",
                                options=[], # Will be populated by callback
                                placeholder="Choose Patient",
                                className="mb-3 form-control-lg border-primary rounded-pill"
                            ),
                        ]),
                        html.Div([
                            dbc.Label("Appointment Date:", html_for="appointment-date-picker", className="fw-bold mb-2"),
                            dcc.DatePickerSingle(
                                id='appointment-date-picker',
                                min_date_allowed=date.today(),
                                initial_visible_month=date.today(),
                                date=date.today(), # Default to today
                                display_format='YYYY-MM-DD',
                                className="mb-3 d-block" # Make it a block element for better spacing
                            ),
                        ]),
                        html.Div([
                            dbc.Label("Appointment Time:", html_for="appointment-time-input", className="fw-bold mb-2"),
                            dbc.Input(
                                id="appointment-time-input",
                                type="time",
                                value=datetime.now().strftime("%H:%M"), # Default to current time
                                className="mb-3 form-control-lg border-primary rounded-pill"
                            ),
                        ]),
                        dbc.Button(
                            "Schedule Appointment", 
                            id="schedule-appointment-btn", 
                            color="primary", 
                            className="w-100 mb-3 btn-lg rounded-pill"
                        ),
                        html.Div(id="schedule-appointment-message", className="mt-3 text-center"),
                        dcc.Link(
                            dbc.Button(
                                [html.I(className="fas fa-arrow-left me-2"), "Back to Doctor Dashboard"], 
                                color="secondary", 
                                className="w-100 mt-4 rounded-pill"
                            ),
                            href="/doctor_dashboard" # Assuming you have a doctor dashboard page
                        )
                    ])
                ], className="shadow-lg border-0 rounded-lg")
            ])
        ])
    ], fluid=True, className="py-4 bg-light")


# Callback to update the header and patient dropdown options based on the logged-in doctor
@callback(
    Output("schedule-app-header", "children"),
    Output("appointment-patient-select", "options"),
    Output("doctor-id-store-schedule-app", "data"),
    Input('user-id-store', 'data'),      # Doctor's ID from session
    Input('user-role-store', 'data'),    # Doctor's role from session
    prevent_initial_call=False # Allow initial call to populate dropdown on page load
)
def update_schedule_app_ui(doctor_id, user_role):
    if user_role != 'doctor' or not doctor_id:
        return "Access Denied", [], None # Or redirect to login

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (doctor_id,))
    doctor_username = cursor.fetchone()[0]
    conn.close()

    header_text = f"Schedule Appointment, Dr. {doctor_username}"
    patient_options = get_all_patients_for_dropdown(doctor_id) # Get patients assigned to this doctor

    return header_text, patient_options, doctor_id


# Callback to handle scheduling an appointment
@callback(
    Output("schedule-appointment-message", "children"),
    Input("schedule-appointment-btn", "n_clicks"),
    State("doctor-id-store-schedule-app", "data"), # Doctor's ID
    State("appointment-patient-select", "value"),  # Patient ID (instead of username)
    State("appointment-date-picker", "date"),
    State("appointment-time-input", "value"),
    prevent_initial_call=True
)
def handle_schedule_appointment(n_clicks, doctor_id, patient_id, app_date, app_time):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    # Validate inputs
    if not all([doctor_id, patient_id, app_date, app_time]):
        return dbc.Alert("Please ensure a doctor is logged in, and select a patient, date, and time.", color="danger")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Fetch doctor_username and patient_username from IDs for storing in appointments table
        cursor.execute("SELECT username FROM users WHERE id = ?", (doctor_id,))
        doctor_username = cursor.fetchone()[0]

        cursor.execute("SELECT username FROM users WHERE id = ?", (patient_id,))
        patient_username = cursor.fetchone()[0]

        # Insert into appointments table
        cursor.execute(
            "INSERT INTO appointments (doctor_id, doctor_username, patient_id, patient_username, appointment_date, appointment_time, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doctor_id, doctor_username, patient_id, patient_username, app_date, app_time, "scheduled")
        )
        conn.commit()
        return dbc.Alert(f"Appointment scheduled for patient {patient_username} on {app_date} at {app_time}.", color="success")
    except sqlite3.Error as e:
        return dbc.Alert(f"Error scheduling appointment: {e}", color="danger")
    finally:
        conn.close()