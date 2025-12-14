import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import json # For handling joint_angles_json
from datetime import datetime

dash.register_page(__name__, path='/doctor_patient_details', title='Patient Details', order=2)

DATABASE_PATH = 'theralink.db'

def get_patient_details(patient_id):
    conn = sqlite3.connect(DATABASE_PATH)
    # Join with users to get username
    patient_df = pd.read_sql_query(f"""
        SELECT p.patient_id, u.username as patient_username, p.name, p.dob, p.gender, p.contact, p.doctor_id
        FROM patients p
        JOIN users u ON p.patient_id = u.id
        WHERE p.patient_id = {patient_id}
    """, conn)
    conn.close()
    return patient_df.iloc[0] if not patient_df.empty else None

def get_patient_sessions(patient_id):
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(f"""
        SELECT *
        FROM sessions
        WHERE patient_id = {patient_id}
        ORDER BY date DESC
    """, conn)
    conn.close()
    return df

# Helper to get doctor's patients
def get_doctor_patients(doctor_id):
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(f"""
        SELECT p.patient_id, p.name, u.username as patient_username
        FROM patients p
        JOIN users u ON p.patient_id = u.id
        WHERE p.doctor_id = {doctor_id}
    """, conn)
    conn.close()
    return df

def list_layout(doctor_username=None):
    # This layout is for listing all patients for the doctor
    return dbc.Container([
        dcc.Store(id='doctor-id-store-patient-list', storage_type='session'),
        html.H1(f"My Patients (Dr. {doctor_username})", className="mb-4 text-center"),
        html.Hr(),
        dbc.Card([
            dbc.CardHeader("Assigned Patients"),
            dbc.CardBody(id="all-patients-list-content") # Populated by callback
        ])
    ], className="mt-4")

def detail_layout():
    # This layout is for showing details of a specific patient
    return dbc.Container([
        dcc.Store(id='selected-patient-id-on-page', storage_type='session'),
        html.H1("Patient Details", className="mb-4 text-center text-primary"),
        html.Hr(),

        dbc.Card([
            dbc.CardHeader(html.H4(id="patient-name-header", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.P(id="patient-username-display"), width=6),
                    dbc.Col(html.P(id="patient-dob"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P(id="patient-gender"), width=6),
                    dbc.Col(html.P(id="patient-contact"), width=6),
                ])
            ])
        ], className="mb-4 shadow-sm"),

        dbc.Card([
            dbc.CardHeader("Session History and Progress"),
            dbc.CardBody([
                dcc.Dropdown(
                    id='patient-session-exercise-filter',
                    options=[], # Options loaded by callback
                    placeholder="Filter by Exercise Type",
                    clearable=True,
                    className="mb-3"
                ),
                dcc.Graph(id='patient-reps-progress-graph'),
                html.Hr(),
                dcc.Graph(id='patient-joint-angle-progress-graph'),
                html.Hr(),
                html.H5("Detailed Session Log"),
                html.Div(id='patient-detailed-session-table', className="mt-3"),
                dbc.Collapse(
                    dbc.Card(dbc.CardBody(id='selected-patient-session-data')),
                    id='patient-session-detail-collapse',
                    is_open=False,
                    className="mt-3"
                )
            ])
        ], className="mb-4 shadow-sm"),
        html.Div(id='dummy-output-patient-details', style={'display': 'none'}) # Dummy for initial callback
    ], className="mt-4")


# Callback for listing all patients a doctor is assigned to
@callback(
    Output('all-patients-list-content', 'children'),
    Output('doctor-id-store-patient-list', 'data'),
    Input('user-id-store', 'data'), # Get doctor ID from app.py
    Input('url', 'pathname') # Trigger on page load
)
def update_all_patients_list(doctor_id, pathname):
    if not doctor_id:
        return html.P("Please log in as a doctor."), dash.no_update
    
    patients_df = get_doctor_patients(doctor_id)
    if patients_df.empty:
        return html.P("You are not assigned to any patients yet."), doctor_id

    patient_cards = [
        dbc.Card(
            dbc.CardBody([
                html.H5(patient['name'], className="card-title"),
                html.P(f"Username: {patient['patient_username']}", className="card-text"),
                dbc.Button(
                    "View Details",
                    id={'type': 'view-patient-details-btn', 'index': patient['patient_id']},
                    className="mt-2",
                    color="primary",
                    href=f"/doctor_patient_details?patient_id={patient['patient_id']}" # Link to detail view
                )
            ]),
            className="mb-3"
        )
        for index, patient in patients_df.iterrows()
    ]
    return patient_cards, doctor_id

# Main layout for the page
# This callback determines whether to show the list view or the detail view
@callback(
    Output(__name__, 'layout'),
    Input('url', 'search'), # Listen for query parameters
    Input('user-id-store', 'data'), # For doctor_username in list layout
    State('user-role-store', 'data') # To check if user is doctor
)
def display_page(url_search, user_id, user_role):
    if user_role != 'doctor':
        return dbc.Container(html.P("Access Denied. Please log in as a doctor."), className="mt-4")

    query_params = dash.get_relative_path(url_search).split('?')
    if len(query_params) > 1:
        query_params = query_params[1]
        params = {k: v for k, v in [p.split('=') for p in query_params.split('&')]}
        if 'patient_id' in params:
            # We are in detail view
            return detail_layout()
    
    # If no patient_id in URL, show the list view
    conn = sqlite3.connect(DATABASE_PATH)
    doctor_username_df = pd.read_sql_query(f"SELECT username FROM users WHERE id = {user_id}", conn)
    conn.close()
    doctor_username = doctor_username_df['username'].iloc[0] if not doctor_username_df.empty else "Unknown"

    return list_layout(doctor_username)


# Callback to populate patient details in the detail view
@callback(
    Output('patient-name-header', 'children'),
    Output('patient-username-display', 'children'),
    Output('patient-dob', 'children'),
    Output('patient-gender', 'children'),
    Output('patient-contact', 'children'),
    Output('selected-patient-id-on-page', 'data'), # Store selected patient ID
    Input('url', 'search'),
    prevent_initial_call=True
)
def update_patient_details_display(url_search):
    query_params = dash.get_relative_path(url_search).split('?')
    if len(query_params) > 1:
        query_params = query_params[1]
        params = {k: v for k, v in [p.split('=') for p in query_params.split('&')]}
        
        patient_id = params.get('patient_id')
        if patient_id:
            patient_id = int(patient_id)
            patient_data = get_patient_details(patient_id)
            if patient_data:
                return (
                    f"{patient_data['name']} (ID: {patient_data['patient_id']})",
                    f"Username: {patient_data['patient_username']}",
                    f"Date of Birth: {patient_data['dob']}",
                    f"Gender: {patient_data['gender']}",
                    f"Contact: {patient_data['contact']}",
                    patient_id
                )
    return "", "", "", "", "", dash.no_update # Default empty or no update


# Callback to populate session data and graphs
@callback(
    Output('patient-session-exercise-filter', 'options'),
    Output('patient-reps-progress-graph', 'figure'),
    Output('patient-joint-angle-progress-graph', 'figure'),
    Output('patient-detailed-session-table', 'children'),
    Input('selected-patient-id-on-page', 'data'),
    Input('patient-session-exercise-filter', 'value'),
    prevent_initial_call=True
)
def update_patient_session_data(patient_id, selected_exercise_type):
    if not patient_id:
        return [], go.Figure(), go.Figure(), html.P("No patient selected.")

    sessions_df = get_patient_sessions(patient_id)
    
    if sessions_df.empty:
        return [], go.Figure(), go.Figure(), html.P("No session data available for this patient.")

    # Convert date to datetime objects for sorting and plotting
    sessions_df['date'] = pd.to_datetime(sessions_df['date'])
    sessions_df = sessions_df.sort_values(by='date')

    # Get unique exercise types for the dropdown
    exercise_options = [{'label': i, 'value': i} for i in sessions_df['exercise_type'].unique()]

    filtered_sessions_df = sessions_df
    if selected_exercise_type:
        filtered_sessions_df = sessions_df[sessions_df['exercise_type'] == selected_exercise_type]
        if filtered_sessions_df.empty:
            return exercise_options, go.Figure(), go.Figure(), html.P(f"No '{selected_exercise_type}' sessions found.")

    # Reps Progress Graph
    reps_fig = px.line(
        filtered_sessions_df,
        x='date',
        y='total_reps',
        color='exercise_type' if not selected_exercise_type else None,
        markers=True,
        title='Total Repetitions Over Time'
    )
    reps_fig.update_layout(xaxis_title="Date", yaxis_title="Total Reps", hovermode="x unified")

    # Joint Angle Progress Graph (more complex - needs to parse JSON)
    joint_angle_fig = go.Figure()
    joint_angle_fig.update_layout(title='Average Joint Angles Over Time', xaxis_title="Date", yaxis_title="Angle (degrees)")

    # Group by exercise type if no specific filter is applied
    if not selected_exercise_type:
        for exercise in filtered_sessions_df['exercise_type'].unique():
            exercise_df = filtered_sessions_df[filtered_sessions_df['exercise_type'] == exercise]
            for joint in ['knee', 'hip', 'ankle', 'shoulder', 'elbow', 'wrist']: # Example joints
                joint_angles_data = []
                dates = []
                for idx, row in exercise_df.iterrows():
                    try:
                        angles_json = json.loads(row['joint_angles_json'])
                        if joint in angles_json:
                            # Assuming joint_angles_json contains a dict like {'knee': [angles], 'hip': [angles]}
                            # We'll take the mean for simplicity for a progress graph
                            joint_angles_data.append(sum(angles_json[joint]) / len(angles_json[joint]))
                            dates.append(row['date'])
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue # Skip if JSON is invalid or joint not found
                if joint_angles_data:
                    joint_angle_fig.add_trace(go.Scatter(
                        x=dates,
                        y=joint_angles_data,
                        mode='lines+markers',
                        name=f"{exercise} - {joint} (Avg)",
                        hovertemplate=
                        '<b>Date</b>: %{x}<br>' +
                        '<b>Avg Angle</b>: %{y:.2f} degrees<br>' +
                        '<extra></extra>' # Hides trace name on hover
                    ))
    else: # Specific exercise selected
        for joint in ['knee', 'hip', 'ankle', 'shoulder', 'elbow', 'wrist']: # Example joints
            joint_angles_data = []
            dates = []
            for idx, row in filtered_sessions_df.iterrows():
                try:
                    angles_json = json.loads(row['joint_angles_json'])
                    if joint in angles_json:
                        joint_angles_data.append(sum(angles_json[joint]) / len(angles_json[joint]))
                        dates.append(row['date'])
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            if joint_angles_data:
                joint_angle_fig.add_trace(go.Scatter(
                    x=dates,
                    y=joint_angles_data,
                    mode='lines+markers',
                    name=f"{selected_exercise_type} - {joint} (Avg)",
                    hovertemplate=
                    '<b>Date</b>: %{x}<br>' +
                    '<b>Avg Angle</b>: %{y:.2f} degrees<br>' +
                    '<extra></extra>'
                ))

    # Detailed Session Table
    # Create a table from the filtered sessions_df
    table_rows = []
    for idx, row in filtered_sessions_df.iterrows():
        table_rows.append(html.Tr([
            html.Td(row['date'].strftime('%Y-%m-%d %H:%M')),
            html.Td(row['exercise_type']),
            html.Td(row['total_reps']),
            html.Td(row['duration_seconds']),
            html.Td(dbc.Button("View Details", id={'type': 'open-session-detail', 'index': row['session_id']}, size="sm", color="info"))
        ]))
    
    detailed_table = dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Date"),
                html.Th("Exercise Type"),
                html.Th("Total Reps"),
                html.Th("Duration (s)"),
                html.Th("Actions")
            ])),
            html.Tbody(table_rows)
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        className="table-sm"
    )

    return exercise_options, reps_fig, joint_angle_fig, detailed_table


# Callback to open/close session detail collapse and display data
@callback(
    Output('patient-session-detail-collapse', 'is_open'),
    Output('selected-patient-session-data', 'children'),
    Input({'type': 'open-session-detail', 'index': dash.ALL}, 'n_clicks'),
    State('patient-session-detail-collapse', 'is_open'),
    prevent_initial_call=True
)
def toggle_session_detail_collapse(n_clicks, is_open):
    if not n_clicks or all(nc is None for nc in n_clicks):
        raise dash.exceptions.PreventUpdate

    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    session_id = json.loads(button_id)['index']

    # Fetch specific session data
    conn = sqlite3.connect(DATABASE_PATH)
    session_df = pd.read_sql_query(f"SELECT * FROM sessions WHERE session_id = {session_id}", conn)
    conn.close()

    if session_df.empty:
        return is_open, html.P("Session data not found.")

    session_data = session_df.iloc[0]
    
    # Parse joint angles and create a more detailed display
    joint_angles_display = html.Ul([
        html.Li(f"{joint.capitalize()}: {angles}")
        for joint, angles in json.loads(session_data['joint_angles_json']).items()
    ])

    detail_content = dbc.Container([
        html.H5(f"Session Details (ID: {session_data['session_id']})", className="mb-3"),
        dbc.Row([
            dbc.Col(html.P(f"Date: {pd.to_datetime(session_data['date']).strftime('%Y-%m-%d %H:%M')}")),
            dbc.Col(html.P(f"Exercise Type: {session_data['exercise_type']}")),
        ]),
        dbc.Row([
            dbc.Col(html.P(f"Total Reps: {session_data['total_reps']}")),
            dbc.Col(html.P(f"Duration: {session_data['duration_seconds']} seconds")),
        ]),
        html.H6("Joint Angles:"),
        joint_angles_display,
        html.H6("Remarks:"),
        html.P(session_data.get('remarks', 'No remarks provided.'))
    ])

    return not is_open, detail_content # Toggle collapse and update content