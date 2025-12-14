import dash
import sys
import os

# Ensure the 'pages' folder is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

from dash import Dash, html, dcc, Input, Output, State, page_container
import dash_bootstrap_components as dbc
import sqlite3
import pandas as pd
import bcrypt # For secure password hashing
from datetime import datetime
import threading
import queue
import time
import webbrowser
from threading import Timer

# Import functions and variables from app_squat.py
# Assuming app_squat.py now manages its own DB init more cleanly
from app_squat import generate_frames, frame_queue, data_queue, start_session, stop_session, session_active, \
    TARGET_REPS, TARGET_SETS, REST_DURATION_SECONDS, current_set, reps_in_current_set, set_rest_active, \
    save_session_data, exercise_duration, create_sessions_table, get_patient_sessions

# Initialize Dash app
external_stylesheets = [
    dbc.themes.SPACELAB, # Or try CERULEAN, FLATLY, PULSE, QUARTZ for different vibes
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css' # For icons
]
app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheets)
server = app.server
app.config.suppress_callback_exceptions = True

# SQLite Database Initialization for main app
DATABASE_PATH = 'theralink.db'

def init_main_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL -- 'patient' or 'doctor'
        )
    ''')

    # Create patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            contact TEXT,
            doctor_id INTEGER,
            FOREIGN KEY (patient_id) REFERENCES users(id),
            FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # Create doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            specialty TEXT,
            contact TEXT,
            FOREIGN KEY (doctor_id) REFERENCES users(id)
        )
    ''')

    # Create appointments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def add_user_if_not_exists(username, password, role, name=None, specialty=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_exists = cursor.fetchone()

    if not user_exists:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, hashed_password, role))
        user_id = cursor.lastrowid

        if role == 'patient':
            # Ensure name is provided or defaults to username
            cursor.execute("INSERT INTO patients (patient_id, name) VALUES (?, ?)", (user_id, name if name else username))
        elif role == 'doctor':
            # Ensure name and specialty are provided or defaults to username/None
            cursor.execute("INSERT INTO doctors (doctor_id, name, specialty) VALUES (?, ?, ?)", (user_id, name if name else username, specialty))
        conn.commit()
        print(f"Added default {role}: {username}")
    conn.close()

# Initialize main database and add default users
init_main_db()
create_sessions_table() # Initialize squat app's sessions table (renamed from init_db)
add_user_if_not_exists('patient1', 'patientpass', 'patient', name='Jane Doe')
add_user_if_not_exists('doctor1', 'doctorpass', 'doctor', name='Dr. Smith', specialty='Physiotherapy')

# Start the video streaming and data processing in a separate thread
video_thread = threading.Thread(target=generate_frames, daemon=True)
video_thread.start()

# Login Layout
login_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Welcome to TheraLink", className="text-center text-primary mb-4"), width=12)),
    dbc.Row(dbc.Col(html.P("Your unified platform for rehabilitation and care.", className="text-center text-muted mb-5"), width=12)),
    dbc.Row(justify="center", children=[
        dbc.Col(md=6, lg=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H4("Login", className="text-center")),
                dbc.CardBody([
                    dbc.Select(
                        id="login-role",
                        options=[{"label": "Patient", "value": "patient"}, {"label": "Doctor", "value": "doctor"}],
                        placeholder="Select Role", className="mb-3 form-control-lg border-primary rounded-pill"
                    ),
                    dbc.Input(id="login-username", placeholder="Username", type="text", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Input(id="login-password", placeholder="Password", type="password", className="mb-4 form-control-lg border-primary rounded-pill"),
                    dbc.Button("Login", id="login-btn", color="primary", className="w-100 mb-3 btn-lg rounded-pill"),
                    dbc.Row([
                        dbc.Col(dbc.Button("Sign Up", id="signup-btn", color="outline-secondary", className="w-100 rounded-pill"), width=6),
                        dbc.Col(dbc.Button("Forgot Password?", id="forgot-btn", color="outline-warning", className="w-100 rounded-pill"), width=6)
                    ], className="mb-3"),
                    html.Div(id="login-message", className="mt-3 text-center")
                ])
            ], className="shadow-lg border-0 rounded-lg")
        ])
    ])
], fluid=True, className="py-5 bg-light")

# Creative Signup Layout
signup_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Join TheraLink", className="text-center text-primary mb-4"), width=12)),
    dbc.Row(justify="center", children=[
        dbc.Col(md=6, lg=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H4("Create Account", className="text-center")),
                dbc.CardBody([
                    dbc.Input(id="signup-username", placeholder="Choose Username", type="text", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Input(id="signup-password", placeholder="Create Password", type="password", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Input(id="signup-confirm-password", placeholder="Confirm Password", type="password", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Select(
                        id="signup-role",
                        options=[{"label": "Patient", "value": "patient"}, {"label": "Doctor", "value": "doctor"}],
                        placeholder="Select Role", className="mb-4 form-control-lg border-primary rounded-pill"
                    ),
                    dbc.Button("Register", id="register-btn", color="primary", className="w-100 mb-3 btn-lg rounded-pill"),
                    dbc.Button("Back to Login", id="back-login-btn", color="outline-secondary", className="w-100 rounded-pill"),
                    html.Div(id="signup-message", className="mt-3 text-center")
                ])
            ], className="shadow-lg border-0 rounded-lg")
        ])
    ])
], fluid=True, className="py-5 bg-light")

# Creative Forgot Password Layout
forgot_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Reset Your Password", className="text-center text-primary mb-4"), width=12)),
    dbc.Row(justify="center", children=[
        dbc.Col(md=6, lg=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H4("New Password", className="text-center")),
                dbc.CardBody([
                    dbc.Input(id="forgot-username", placeholder="Enter your username", type="text", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Input(id="new-password", placeholder="Create New Password", type="password", className="mb-3 form-control-lg border-primary rounded-pill"),
                    dbc.Input(id="confirm-new-password", placeholder="Confirm New Password", type="password", className="mb-4 form-control-lg border-primary rounded-pill"),
                    dbc.Button("Change Password", id="reset-btn", color="primary", className="w-100 mb-3 btn-lg rounded-pill"),
                    dbc.Button("Back to Login", id="back-login2-btn", color="outline-secondary", className="w-100 rounded-pill"),
                    html.Div(id="forgot-message", className="mt-3 text-center")
                ])
            ], className="shadow-lg border-0 rounded-lg")
        ])
    ])
], fluid=True, className="py-5 bg-light")

def get_navbar(user_role, username):
    if user_role == "doctor":
        return dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Dashboard", href="/doctor_dashboard", style={"color":"white"})),
                dbc.NavItem(dbc.NavLink("My Patients", href="/doctor_patient_details", style={"color":"white"})), # Adjusted href for pages
                dbc.NavItem(dbc.NavLink("Schedule Appointment", href="/doctor_schedule_appointment", style={"color":"white"})), # Adjusted href for pages
                dbc.NavItem(
                    dbc.NavLink(
                        [html.I(className="fas fa-bell me-1"), "Notifications ", dbc.Badge(id="doctor-notification-badge", color="danger", pill=True, className="ms-1", children="0")],
                        href="#", id="notification-toggle", n_clicks=0, style={"color":"white"}
                    ),
                    className="position-relative",
                    id="doctor-notification-navitem"
                ),
                dbc.DropdownMenu(
                    children=[
                        dbc.DropdownMenuItem("No new notifications", id="no-notifications-item"),
                        dbc.DropdownMenuItem(divider=True),
                        dcc.Loading(dbc.DropdownMenuItem(id="doctor-notifications-list", children=[])),
                    ],
                    nav=True,
                    in_navbar=True,
                    label="",
                    id="notification-dropdown",
                    toggle_style={"visibility": "hidden", "width": "0px", "padding": "0px"},
                    direction="left",
                    className="position-absolute end-0 top-100 mt-2",
                    style={"zIndex": 1050}
                ),
                dbc.NavItem(dbc.NavLink("Logout", href="/", id="logout-link", style={"color":"white"})) # Logout goes to root
            ],
            brand=f"TheraLink (Dr. {username})", color="dark", dark=True, className="mb-4"
        )
    elif user_role == "patient":
        return dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Dashboard", href="/patient_dashboard", style={"color":"white"})),
                dbc.NavItem(dbc.NavLink("My Sessions", href="/patient_sessions", style={"color":"white"})),
                dbc.NavItem(dbc.NavLink("Squat App", href="/squat_app", style={"color":"white"})), # Link to your squat app
                dbc.NavItem(dbc.NavLink("Logout", href="/", id="logout-link", style={"color":"white"})) # Logout goes to root
            ],
            brand=f"TheraLink (Patient {username})", color="dark", dark=True, className="mb-4"
        )
    else:
        return None

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="user-role", storage_type="session"),
    dcc.Store(id="username-store", storage_type="session"),
    dcc.Store(id="user-id-store", storage_type="session"), # Store user ID
    dcc.Store(id="selected-patient-id", storage_type="session"), # Use ID instead of username for patient selection
    html.Div(id="navbar-container"),
    html.Div(id="page-content"), # This will now render page_container
    dcc.Interval(
        id='notification-interval',
        interval=10*1000, # Check every 10 seconds
        n_intervals=0,
        disabled=True
    ),
    # Hidden components for squat app interactions
    dcc.Interval(id='video-update-interval', interval=100, n_intervals=0, disabled=True),
    dcc.Interval(id='graph-update-interval', interval=1000, n_intervals=0, disabled=True),
    html.Div(id='dummy-output-for-notification-click', style={'display': 'none'}) # Dummy output for notification click
])

@app.callback(
    Output("page-content", "children"),
    Output("navbar-container", "children"),
    Output("notification-interval", "disabled"),
    # Squat app specific outputs to control intervals
    Output("video-update-interval", "disabled"),
    Output("graph-update-interval", "disabled"),
    Input("url", "pathname"),
    State("user-role", "data"),
    State("username-store", "data")
)
def render_page_and_navbar(pathname, role, username):
    navbar = get_navbar(role, username)
    disable_notifications = True
    disable_video_update = True
    disable_graph_update = True

    # If not logged in, show login page. Otherwise, show page_container
    if role is None:
        if pathname == "/signup":
            return signup_layout, None, True, True, True
        elif pathname == "/forgot":
            return forgot_layout, None, True, True, True
        else: # Default to login for any other path if not logged in
            return login_layout, None, True, True, True
    
    # If logged in, handle specific page requirements
    if role == "doctor":
        disable_notifications = False
    
    # Enable squat app intervals only when on the squat app page
    # Ensure this check matches the actual page path for the squat app
    if pathname == "/squat_app" and role == "patient":
        disable_video_update = False
        disable_graph_update = False

    return page_container, navbar, disable_notifications, disable_video_update, disable_graph_update


# Authentication Callbacks
@app.callback(
    Output("login-message", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Output("user-role", "data", allow_duplicate=True),
    Output("username-store", "data", allow_duplicate=True),
    Output("user-id-store", "data", allow_duplicate=True),
    Input("login-btn", "n_clicks"),
    State("login-role", "value"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def handle_login(n_clicks, login_role, login_user, login_pass):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    if not all([login_role, login_user, login_pass]):
        return dbc.Alert("All fields required!", color="danger"), dash.no_update, None, None, None

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username=? AND role=?", (login_user, login_role))
    record = cursor.fetchone()
    conn.close()

    if record:
        user_id, hashed_password = record
        if bcrypt.checkpw(login_pass.encode('utf-8'), hashed_password.encode('utf-8')):
            page_path = "/" + login_role + "_dashboard" # e.g., "/doctor_dashboard" or "/patient_dashboard"
            return "", page_path, login_role, login_user, user_id
        else:
            return dbc.Alert("Invalid credentials!", color="danger"), dash.no_update, None, None, None
    else:
        return dbc.Alert("Invalid credentials!", color="danger"), dash.no_update, None, None, None


@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("signup-btn", "n_clicks"),
    prevent_initial_call=True
)
def navigate_to_signup(n_clicks):
    if n_clicks:
        return "/signup"
    return dash.no_update

@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("forgot-btn", "n_clicks"),
    prevent_initial_call=True
)
def navigate_to_forgot(n_clicks):
    if n_clicks:
        return "/forgot"
    return dash.no_update

@app.callback(
    Output("signup-message", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("register-btn", "n_clicks"),
    Input("back-login-btn", "n_clicks"),
    State("signup-username", "value"),
    State("signup-password", "value"),
    State("signup-confirm-password", "value"),
    State("signup-role", "value"),
    prevent_initial_call=True
)
def handle_signup_and_back(register_n_clicks, back_n_clicks, signup_user, signup_pass, signup_confirm, signup_role):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "back-login-btn" and back_n_clicks:
        return "", "/" # Go to login page
    
    if trigger_id == "register-btn" and register_n_clicks:
        if not all([signup_user, signup_pass, signup_confirm, signup_role]):
            return dbc.Alert("All fields required!", color="danger"), dash.no_update
        elif signup_pass != signup_confirm:
            return dbc.Alert("Passwords do not match!", color="danger"), dash.no_update
        else:
            try:
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                # Check if username already exists
                cursor.execute("SELECT id FROM users WHERE username = ?", (signup_user,))
                if cursor.fetchone():
                    conn.close()
                    return dbc.Alert("Username already exists!", color="danger"), dash.no_update

                hashed_password = bcrypt.hashpw(signup_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("INSERT INTO users(username,password,role) VALUES (?,?,?)",
                               (signup_user, hashed_password, signup_role))
                user_id = cursor.lastrowid # Get the ID of the newly inserted user
                
                # Add entry to patient or doctor table
                if signup_role == 'patient':
                    cursor.execute("INSERT INTO patients (patient_id, name) VALUES (?, ?)", (user_id, signup_user))
                elif signup_role == 'doctor':
                    cursor.execute("INSERT INTO doctors (doctor_id, name) VALUES (?, ?)", (user_id, signup_user))

                conn.commit()
                conn.close()
                return dbc.Alert("Registration successful! You can login now.", color="success"), "/"
            except sqlite3.IntegrityError as e: # Catch potential unique constraint errors (though checked above)
                return dbc.Alert(f"Registration failed: {e}", color="danger"), dash.no_update

    return dash.no_update, dash.no_update


@app.callback(
    Output("forgot-message", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("reset-btn", "n_clicks"),
    Input("back-login2-btn", "n_clicks"),
    State("forgot-username", "value"),
    State("new-password", "value"),
    State("confirm-new-password", "value"),
    prevent_initial_call=True
)
def handle_forgot_and_back(reset_n_clicks, back_n_clicks, forgot_user, new_pass, confirm_pass):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "back-login2-btn" and back_n_clicks:
        return "", "/"

    if trigger_id == "reset-btn" and reset_n_clicks:
        if not all([forgot_user, new_pass, confirm_pass]):
            return dbc.Alert("All fields required!", color="danger"), dash.no_update
        
        if new_pass != confirm_pass:
            return dbc.Alert("New passwords do not match!", color="danger"), dash.no_update

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (forgot_user,))
        user_record = cursor.fetchone()
        
        if not user_record:
            conn.close()
            return dbc.Alert("Username not found!", color="danger"), dash.no_update
        else:
            hashed_password = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE users SET password=? WHERE username=?", (hashed_password, forgot_user))
            conn.commit()
            conn.close()
            
            return dbc.Alert("Password successfully changed. Please log in.", color="success"), "/"

    return dash.no_update, dash.no_update

# Logout Callback
@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("user-role", "data", allow_duplicate=True),
    Output("username-store", "data", allow_duplicate=True),
    Output("user-id-store", "data", allow_duplicate=True),
    Input("logout-link", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks is not None and n_clicks > 0:
        # Clear all session stores on logout
        return "/", None, None, None
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Doctor Notification Callbacks
@app.callback(
    Output("doctor-notification-badge", "children"),
    Output("doctor-notifications-list", "children"),
    Output("notification-dropdown", "is_open"),
    Input("notification-interval", "n_intervals"),
    Input("notification-toggle", "n_clicks"),
    State("user-id-store", "data"), # Use doctor_id for queries
    State("notification-dropdown", "is_open"),
    prevent_initial_call=True
)
def update_doctor_notifications(n_intervals, toggle_clicks, doctor_id, is_open):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    if trigger_id == "notification-toggle":
        # Toggle dropdown open/close but don't re-fetch on click
        return dash.no_update, dash.no_update, not is_open

    # This part runs on interval or initial load if not triggered by toggle
    if doctor_id: # Use doctor_id for queries
        conn = sqlite3.connect('squat_sessions.db') # Connect to the squat sessions DB
        cursor = conn.cursor()
        # Find sessions assigned to this doctor where a report was generated (report_generated = 1)
        # Need to join with users table (from theralink.db) to get patient_username
        # This requires a more complex query if the sessions table only has patient_id
        # Let's assume for simplicity `squat_sessions.db` sessions table has patient_id, and we fetch patient name from `theralink.db`
        
        # First, get notifications from squat_sessions.db
        cursor.execute("""
            SELECT patient_id, exercise_type, date, session_id
            FROM sessions
            WHERE doctor_id = ? AND report_generated = 1
            ORDER BY date DESC
        """, (doctor_id,))
        notifications_raw = cursor.fetchall()
        conn.close()

        if notifications_raw:
            notification_items = []
            badge_count = len(notifications_raw)
            
            # Fetch patient names from main DB
            patient_ids_in_notifications = [n[0] for n in notifications_raw]
            if patient_ids_in_notifications:
                conn_main = sqlite3.connect(DATABASE_PATH)
                cursor_main = conn_main.cursor()
                placeholders = ','.join('?' * len(patient_ids_in_notifications))
                cursor_main.execute(f"SELECT patient_id, name FROM patients WHERE patient_id IN ({placeholders})", patient_ids_in_notifications)
                patient_names_map = {row[0]: row[1] for row in cursor_main.fetchall()}
                conn_main.close()

                for patient_id, exercise_type, session_date, session_id in notifications_raw:
                    patient_name = patient_names_map.get(patient_id, f"Patient {patient_id}")
                    notification_items.append(
                        dbc.DropdownMenuItem(
                            f"Report for {patient_name} ({exercise_type}) - {session_date.split(' ')[0]}", # Just date part
                            id={'type': 'notification-item', 'index': session_id}
                        )
                    )
            else:
                 return "0", [dbc.DropdownMenuItem("No new notifications", id="no-notifications-item")], dash.no_update

            return str(badge_count), notification_items, dash.no_update
        else:
            return "0", [dbc.DropdownMenuItem("No new notifications", id="no-notifications-item")], dash.no_update
    
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output("dummy-output-for-notification-click", "children"), # This is just to trigger, no actual content needed
    Input({'type': 'notification-item', 'index': dash.ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def mark_notification_viewed(n_clicks_list):
    # n_clicks_list will be a list of n_clicks for each matching component.
    # We only care if any of them were clicked.
    if not any(n_clicks_list) or all(n is None for n in n_clicks_list):
        raise dash.exceptions.PreventUpdate
    
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_input = ctx.triggered[0]['prop_id']
    # The ID structure is {'type': 'notification-item', 'index': session_id}.n_clicks
    # We need to parse the dictionary part to get the session_id
    session_id_str = triggered_input.split('.')[0]
    session_id = eval(session_id_str)['index'] # Convert string dict to actual dict and get index

    conn = sqlite3.connect('squat_sessions.db') # Connect to the squat sessions DB
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET report_generated = 0 WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

    return "" # Return empty string for dummy output


# Navigate to patient details (Doctor Dashboard)
@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("selected-patient-id", "data", allow_duplicate=True),
    Input({'type': 'view-patient-btn', 'index': dash.ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def navigate_to_patient_details(n_clicks_list):
    # This callback can be triggered by multiple buttons, so we check which one was clicked
    if not any(n_clicks_list) or all(n is None for n in n_clicks_list):
        raise dash.exceptions.PreventUpdate
    
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id_dict = eval(button_id_str) # Convert string representation of dict to actual dict
    
    if button_id_dict['type'] == 'view-patient-btn':
        patient_id = button_id_dict['index']
        # Navigate to the patient details page and store the selected patient's ID
        return "/doctor_patient_details", patient_id
    
    return dash.no_update, dash.no_update


# Open browser automatically
if __name__ == "__main__":
    def open_browser():
        if not webbrowser.open_new("http://127.0.0.1:8051/"):
            print("Webbrowser could not be opened. Please navigate to http://127.0.0.1:8051/ manually.")

    Timer(1, open_browser).start()
    app.run_server(debug=True, port=8051)