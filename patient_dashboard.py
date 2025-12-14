import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

dash.register_page(__name__, path='/patient_dashboard', title='Patient Dashboard', order=1)

DATABASE_PATH = 'theralink.db'

def get_patient_sessions_summary(patient_id):
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(f"""
        SELECT date, exercise_type, reps_achieved, reps_target, sets_achieved, sets_target, exercise_duration
        FROM sessions
        WHERE patient_id = {patient_id}
        ORDER BY date DESC
    """, conn)
    conn.close()
    return df

def get_upcoming_appointments_patient(patient_id):
    conn = sqlite3.connect(DATABASE_PATH)
    # Join with users table to get doctor username
    df = pd.read_sql_query(f"""
        SELECT u.username as doctor_username, a.appointment_date, a.appointment_time
        FROM appointments a
        JOIN users u ON a.doctor_id = u.id
        WHERE a.patient_id = {patient_id} AND a.status = 'Scheduled'
        AND a.appointment_date >= DATE('now')
        ORDER BY a.appointment_date, a.appointment_time
    """, conn)
    conn.close()
    return df

def layout(patient_username=None):
    return dbc.Container([
        dcc.Store(id='patient-id-store-page', storage_type='session'), # Store for patient's own ID
        html.H1(f"Welcome, {patient_username}", className="mb-4 text-center text-primary"),
        html.Hr(),

        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Your Progress Summary"),
                    dbc.CardBody(id="patient-dashboard-progress-summary") # Content updated by callback
                ]),
                md=6, className="mb-4"
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Upcoming Appointments"),
                    dbc.CardBody(id="patient-dashboard-appointments") # Content updated by callback
                ]),
                md=6, className="mb-4"
            )
        ]),

        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Your Recent Sessions"),
                    dbc.CardBody(id="patient-dashboard-recent-sessions") # Content updated by callback
                ]),
                width=12, className="mb-4"
            )
        ]),
        html.Div(id='dummy-output-patient-dashboard', style={'display': 'none'}) # Dummy output for initial callbacks
    ], className="mt-4")


@callback(
    Output('patient-id-store-page', 'data'),
    Input('user-id-store', 'data'), # From app.py
    prevent_initial_call=True
)
def store_patient_id(user_id):
    return user_id

@callback(
    Output('patient-dashboard-progress-summary', 'children'),
    Output('patient-dashboard-appointments', 'children'),
    Output('patient-dashboard-recent-sessions', 'children'),
    Input('patient-id-store-page', 'data'), # Use the page-specific store
    Input('url', 'pathname') # Trigger update on page load
)
def update_patient_dashboard(patient_id, pathname):
    if not patient_id:
        return html.P("Please log in as a patient to view this dashboard."), \
               html.P("Please log in as a patient to view this dashboard."), \
               html.P("Please log in as a patient to view this dashboard.")

    # Progress Summary
    sessions_df = get_patient_sessions_summary(patient_id)
    progress_summary_content = html.P("No sessions recorded yet.")
    if not sessions_df.empty:
        # Example: Simple summary metrics
        total_reps = sessions_df['reps_achieved'].sum()
        total_sessions = len(sessions_df)
        avg_duration = sessions_df['exercise_duration'].mean() / 60 if total_sessions > 0 else 0

        progress_summary_content = dbc.ListGroup([
            dbc.ListGroupItem(f"Total Sessions: {total_sessions}"),
            dbc.ListGroupItem(f"Total Reps Achieved: {total_reps}"),
            dbc.ListGroupItem(f"Average Session Duration: {avg_duration:.1f} minutes"),
            # You can add more complex graphs here, e.g., using Plotly
            dbc.ListGroupItem(
                dcc.Graph(figure=px.line(sessions_df.sort_values('date'), x='date', y='reps_achieved',
                                         title='Reps Over Time', markers=True))
            )
        ], flush=True)

    # Upcoming Appointments
    appointments_df = get_upcoming_appointments_patient(patient_id)
    if not appointments_df.empty:
        appointment_list_items = []
        for index, row in appointments_df.iterrows():
            appointment_list_items.append(
                dbc.ListGroupItem(f"Dr. {row['doctor_username']} - {row['appointment_date']} at {row['appointment_time']}")
            )
        appointment_list_card = dbc.ListGroup(appointment_list_items, flush=True)
    else:
        appointment_list_card = html.P("No upcoming appointments.")

    # Recent Sessions List
    if not sessions_df.empty:
        recent_sessions_list = []
        for index, row in sessions_df.head(5).iterrows(): # Show top 5 recent
            recent_sessions_list.append(
                dbc.ListGroupItem([
                    html.Strong(f"{row['exercise_type']} on {pd.to_datetime(row['date']).strftime('%Y-%m-%d')}"),
                    html.Br(),
                    f"Reps: {row['reps_achieved']}/{row['reps_target']}, Sets: {row['sets_achieved']}/{row['sets_target']}",
                    html.Br(),
                    f"Duration: {row['exercise_duration'] // 60}m {row['exercise_duration'] % 60}s"
                ])
            )
        recent_sessions_card = dbc.ListGroup(recent_sessions_list, flush=True)
    else:
        recent_sessions_card = html.P("No recent sessions to display.")

    return progress_summary_content, appointment_list_card, recent_sessions_card