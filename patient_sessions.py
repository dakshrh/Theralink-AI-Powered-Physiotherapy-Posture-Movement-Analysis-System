import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

dash.register_page(__name__, path='/patient_sessions', title='Your Sessions', order=2)

# Sample data for demonstration
# In a real application, this would come from a database query
sample_sessions_data = {
    'session_id': [1, 2, 3, 4, 5],
    'date': ['2023-10-26', '2023-11-02', '2023-11-09', '2023-11-16', '2023-11-23'],
    'exercise_type': ['Squats', 'Squats', 'Squats', 'Squats', 'Squats'],
    'reps_achieved': [10, 12, 10, 15, 14],
    'reps_target': [10, 12, 12, 15, 15],
    'sets_achieved': [3, 3, 3, 3, 3],
    'sets_target': [3, 3, 3, 3, 3],
    'completion_status': ['Completed', 'Completed', 'Completed', 'Completed', 'Completed'],
    'feedback': ['Good form', 'Excellent!', 'Needs improvement on depth', 'Great progress', 'Maintain form'],
    'joint_angles': [
        {'knee_angle': [90, 85, 92], 'hip_angle': [70, 65, 72]},
        {'knee_angle': [88, 82, 90], 'hip_angle': [68, 62, 70]},
        {'knee_angle': [95, 90, 97], 'hip_angle': [75, 70, 77]},
        {'knee_angle': [85, 80, 88], 'hip_angle': [65, 60, 68]},
        {'knee_angle': [87, 83, 89], 'hip_angle': [67, 63, 69]},
    ],
    'exercise_duration': [300, 320, 310, 290, 315] # in seconds
}
sample_df = pd.DataFrame(sample_sessions_data)
sample_df['date'] = pd.to_datetime(sample_df['date'])


# Assume we have a way to get the current logged-in patient's ID
# For demonstration, let's hardcode a patient ID
CURRENT_PATIENT_ID = 1

layout = dbc.Container([
    dcc.Store(id='patient-id-store', data=CURRENT_PATIENT_ID),
    dcc.Store(id='sessions-data-store', data=sample_sessions_data),

    html.H1("Your Session History", className="mb-4 text-center"),

    dbc.Card([
        dbc.CardHeader(html.H4("Session Overview", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Filter by Exercise Type:", className="fw-bold"),
                    dcc.Dropdown(
                        id='exercise-type-filter',
                        options=[{'label': et, 'value': et} for et in sample_df['exercise_type'].unique()],
                        placeholder="Select an exercise type",
                        clearable=True,
                        className="mb-3"
                    ),
                ], width=6),
                dbc.Col([
                    html.Label("Filter by Date Range:", className="fw-bold"),
                    dcc.DatePickerRange(
                        id='date-range-filter',
                        start_date_placeholder_text="Start Date",
                        end_date_placeholder_text="End Date",
                        clearable=True,
                        className="mb-3"
                    ),
                ], width=6),
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='reps-progress-graph'), width=12),
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col(dcc.Graph(id='duration-progress-graph'), width=12),
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col(dcc.Graph(id='joint-angle-progress-graph'), width=12),
            ]),
        ])
    ], className="mb-4"),

    dbc.Card([
        dbc.CardHeader(html.H4("Detailed Session Log", className="mb-0")),
        dbc.CardBody([
            html.Div(id='session-details-table'),
            dbc.Collapse(
                dbc.Card(dbc.CardBody(id='selected-session-data')),
                id='session-detail-collapse',
                is_open=False,
                className="mt-3"
            )
        ])
    ])
], className="mt-4")

@callback(
    Output('reps-progress-graph', 'figure'),
    Output('duration-progress-graph', 'figure'),
    Output('joint-angle-progress-graph', 'figure'),
    Output('session-details-table', 'children'),
    Input('sessions-data-store', 'data'),
    Input('exercise-type-filter', 'value'),
    Input('date-range-filter', 'start_date'),
    Input('date-range-filter', 'end_date'),
)
def update_session_data_and_graphs(stored_data, selected_exercise_type, start_date, end_date):
    df = pd.DataFrame(stored_data)
    df['date'] = pd.to_datetime(df['date'])

    filtered_df = df.copy()

    if selected_exercise_type:
        filtered_df = filtered_df[filtered_df['exercise_type'] == selected_exercise_type]
    if start_date:
        filtered_df = filtered_df[filtered_df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[filtered_df['date'] <= pd.to_datetime(end_date)]

    # Sort by date for proper graph display
    filtered_df = filtered_df.sort_values(by='date')

    if filtered_df.empty:
        no_data_message = html.Div("No data available for the selected filters.", className="text-center text-muted p-4")
        return go.Figure(), go.Figure(), go.Figure(), no_data_message

    # Reps Progress Graph
    reps_fig = go.Figure()
    reps_fig.add_trace(go.Scatter(x=filtered_df['date'], y=filtered_df['reps_achieved'],
                                  mode='lines+markers', name='Reps Achieved'))
    reps_fig.add_trace(go.Scatter(x=filtered_df['date'], y=filtered_df['reps_target'],
                                  mode='lines+markers', name='Reps Target',
                                  line=dict(dash='dash')))
    reps_fig.update_layout(title='Reps Achieved vs. Target Over Time',
                           xaxis_title='Date', yaxis_title='Number of Reps',
                           legend_title='Metric')

    # Exercise Duration Graph
    duration_fig = px.line(filtered_df, x='date', y='exercise_duration', markers=True,
                           title='Exercise Duration Over Time')
    duration_fig.update_layout(xaxis_title='Date', yaxis_title='Duration (seconds)')

    # Joint Angle Progress Graph (Example: Knee Angle during Squats)
    # This will take the average/min/max of the joint angles recorded in each session
    # For simplicity, let's plot the first recorded knee angle for each session
    if 'joint_angles' in filtered_df.columns and not filtered_df['joint_angles'].isnull().all():
        filtered_df['avg_knee_angle'] = filtered_df['joint_angles'].apply(
            lambda x: x['knee_angle'][0] if x and 'knee_angle' in x and len(x['knee_angle']) > 0 else None
        )
        filtered_df['avg_hip_angle'] = filtered_df['joint_angles'].apply(
            lambda x: x['hip_angle'][0] if x and 'hip_angle' in x and len(x['hip_angle']) > 0 else None
        )

        # Drop rows where angles couldn't be extracted
        filtered_df_angles = filtered_df.dropna(subset=['avg_knee_angle', 'avg_hip_angle'])

        joint_angle_fig = go.Figure()
        if not filtered_df_angles.empty:
            joint_angle_fig.add_trace(go.Scatter(x=filtered_df_angles['date'], y=filtered_df_angles['avg_knee_angle'],
                                                 mode='lines+markers', name='Avg Knee Angle (Degrees)'))
            joint_angle_fig.add_trace(go.Scatter(x=filtered_df_angles['date'], y=filtered_df_angles['avg_hip_angle'],
                                                 mode='lines+markers', name='Avg Hip Angle (Degrees)'))
        joint_angle_fig.update_layout(title='Joint Angle Progress (First Rep)',
                                      xaxis_title='Date', yaxis_title='Angle (Degrees)',
                                      legend_title='Joint')
    else:
        joint_angle_fig = go.Figure().set_layout(title="No Joint Angle Data Available")


    # Session Details Table
    table_header = [
        html.Thead(html.Tr([
            html.Th("Date"), html.Th("Exercise"), html.Th("Reps (Ach/Targ)"),
            html.Th("Sets (Ach/Targ)"), html.Th("Status"), html.Th("Feedback"), html.Th("Details")
        ]))
    ]

    table_rows = []
    for index, row in filtered_df.iterrows():
        table_rows.append(html.Tr([
            html.Td(row['date'].strftime('%Y-%m-%d')),
            html.Td(row['exercise_type']),
            html.Td(f"{row['reps_achieved']}/{row['reps_target']}"),
            html.Td(f"{row['sets_achieved']}/{row['sets_target']}"),
            html.Td(row['completion_status']),
            html.Td(row['feedback']),
            html.Td(dbc.Button("View", id={'type': 'open-session-modal', 'index': row['session_id']},
                               color="info", size="sm"))
        ]))
    table_body = [html.Tbody(table_rows)]

    table = dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True)

    return reps_fig, duration_fig, joint_angle_fig, table


@callback(
    Output('session-detail-collapse', 'is_open'),
    Output('selected-session-data', 'children'),
    Input({'type': 'open-session-modal', 'index': dash.ALL}, 'n_clicks'),
    State('sessions-data-store', 'data'),
    State('session-detail-collapse', 'is_open'),
    prevent_initial_call=True
)
def toggle_session_details(n_clicks, stored_data, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    # Check if any button was clicked
    if any(n_click is not None for n_click in n_clicks):
        # Extract the session_id from the clicked button's ID
        clicked_session_id = eval(button_id)['index'] # eval to convert string dict to dict

        df = pd.DataFrame(stored_data)
        selected_session = df[df['session_id'] == clicked_session_id].iloc[0]

        details = [
            html.P(f"Session ID: {selected_session['session_id']}"),
            html.P(f"Date: {selected_session['date'].strftime('%Y-%m-%d')}"),
            html.P(f"Exercise Type: {selected_session['exercise_type']}"),
            html.P(f"Reps Achieved: {selected_session['reps_achieved']} (Target: {selected_session['reps_target']})"),
            html.P(f"Sets Achieved: {selected_session['sets_achieved']} (Target: {selected_session['sets_target']})"),
            html.P(f"Completion Status: {selected_session['completion_status']}"),
            html.P(f"Feedback: {selected_session['feedback']}"),
            html.P(f"Duration: {selected_session['exercise_duration']} seconds"),
        ]

        # Add detailed joint angle information if available
        if selected_session['joint_angles']:
            details.append(html.H5("Joint Angle Details:"))
            for joint, angles in selected_session['joint_angles'].items():
                details.append(html.P(f"{joint.replace('_', ' ').title()} Angles (Degrees): {', '.join(map(str, angles))}"))

        return not is_open, details
    return is_open, ""