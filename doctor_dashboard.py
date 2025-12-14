from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

# Dummy data for demonstration
df_patients = pd.DataFrame({
    "Day": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "Patients": [5, 7, 3, 8, 6]
})
df_reports = pd.DataFrame({
    "Status": ["Completed", "Pending"],
    "Count": [25, 10]
})

bar_fig = px.bar(df_patients, x="Day", y="Patients", title="Patients per Day", text_auto=True)
pie_fig = px.pie(df_reports, names="Status", values="Count", title="Reports Status")

layout = dbc.Container([
    html.H2("Doctor Dashboard", className="text-center my-4"),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Total Patients"),
            dbc.CardBody(html.H3("42", className="text-success"))
        ], className="shadow"), width=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Appointments Today"),
            dbc.CardBody(html.H3("8", className="text-primary"))
        ], className="shadow"), width=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Pending Reports"),
            dbc.CardBody(html.H3("10", className="text-danger"))
        ], className="shadow"), width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Patients Analytics"),
            dbc.CardBody(dcc.Graph(figure=bar_fig))
        ], className="shadow mb-4"), width=6),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Reports Analytics"),
            dbc.CardBody(dcc.Graph(figure=pie_fig))
        ], className="shadow mb-4"), width=6),
    ])
], fluid=True)
