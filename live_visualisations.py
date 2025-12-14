from threading import Timer
import webbrowser
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import plotly.express as px

# Initialize empty lists for plot data
y_axis_neck, y_axis_knee, y_axis_hip, y_axis_ankle, y_axis_kneey = [0], [0], [0], [0], [0]
x_axis_neck, x_axis_hip, x_axis_knee, x_axis_ankle, x_axis_kneey = [0], [0], [0], [0], [0]

# Load dummy data from CSV. Note: This file must exist for the app to run.
# data/visual_plotting.csv
# e.g.,
# neck,knee,hip,ankle,knee-y
# 0.7,0.8,0.9,1.0,0.75
# 0.8,0.9,1.0,1.1,0.85
data = pd.read_csv("data/visual_plotting.csv")

exponentiation = np.array([2.718 ** i for i in range(10)])
normaliser = np.sum(exponentiation)
exponentiation = exponentiation / normaliser

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__)

# Main app layout with an interval component for live updates
app.layout = html.Div([
    dcc.Interval(
        id='interval-component',
        interval=200,  # in milliseconds
        n_intervals=0
    ),
    html.H1('Live Posture Analytics Dashboard', style={'textAlign': 'center', 'color': '#333', 'marginBottom': '20px'}),
    html.Div([
        html.Div([
            html.H2('NECK', style={'textAlign': 'center', 'color': '#555'}),
            dcc.Graph(id='neck-graph', style={'background': '#FFFFFF', 'height':'300px', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
        ], className='graph-container', style={'flex': '1'}),
        html.Div([
            html.H2('KNEE', style={'textAlign': 'center', 'color': '#555'}),
            dcc.Graph(id='knee-graph', style={'background': '#FFFFFF', 'height':'300px', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
        ], className='graph-container', style={'flex': '1'}),
        html.Div([
            html.H2('HIP', style={'textAlign': 'center', 'color': '#555'}),
            dcc.Graph(id='hip-graph', style={'background': '#FFFFFF', 'height':'300px', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
        ], className='graph-container', style={'flex': '1'}),
        html.Div([
            html.H2('ANKLE', style={'textAlign': 'center', 'color': '#555'}),
            dcc.Graph(id='ankle-graph', style={'background': '#FFFFFF', 'height':'300px', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
        ], className='graph-container', style={'flex': '1'}),
        html.Div([
            html.H2('KNEE-Y', style={'textAlign': 'center', 'color': '#555'}),
            dcc.Graph(id='knee-y-graph', style={'background': '#FFFFFF', 'height':'300px', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
        ], className='graph-container', style={'flex': '1'}),
    ], style={'display':'flex', 'flexDirection':'column', 'gap':'20px', 'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'})
], style={'backgroundColor': '#FFFFFF'})

# Callback for updating the Neck graph
@app.callback(Output('neck-graph', 'figure'), [Input('interval-component', 'n_intervals')])
def update_neck(n):
    global y_axis_neck, x_axis_neck, data
    # Ensure data length matches exponentiation array
    if len(data['neck']) != len(exponentiation):
        temp_y = 0
    else:
        temp_y = np.dot(np.array(data['neck']), exponentiation)
    
    temp_x = x_axis_neck[-1] + 1
    
    # Maintain a fixed number of points on the graph
    if len(x_axis_neck) > 200:
        x_axis_neck.pop(0)
        y_axis_neck.pop(0)
        
    x_axis_neck.append(temp_x)
    y_axis_neck.append(temp_y)
    
    fig = go.Figure()
    # Update title and axis ranges for clarity
    fig.update_layout(title="Neck Joint", xaxis_title="Frame", yaxis_title="Value", yaxis_range=[0.5, 1.5], plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF')
    # Now correctly plotting the dynamic lists with a visible color
    fig.add_trace(go.Scatter(x=x_axis_neck, y=y_axis_neck, mode='lines+markers', name='neck', line=dict(color='black', width=3)))
    return fig

# Callback for updating the Knee graph
@app.callback(Output('knee-graph', 'figure'), [Input('interval-component', 'n_intervals')])
def update_knee(n):
    global y_axis_knee, x_axis_knee, data
    if len(data['knee']) != len(exponentiation):
        temp_y = 0
    else:
        temp_y = np.dot(np.array(data['knee']), exponentiation)

    temp_x = x_axis_knee[-1] + 1
    if len(x_axis_knee) > 200:
        x_axis_knee.pop(0)
        y_axis_knee.pop(0)
        
    x_axis_knee.append(temp_x)
    y_axis_knee.append(temp_y)
    
    fig = go.Figure()
    fig.update_layout(title="Knee Joint", xaxis_title="Frame", yaxis_title="Value", yaxis_range=[0.5, 1.5], plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF')
    fig.add_trace(go.Scatter(x=x_axis_knee, y=y_axis_knee, mode='lines+markers', name='knee', line=dict(color='green', width=3)))
    return fig

# Callback for updating the Hip graph
@app.callback(Output('hip-graph', 'figure'), [Input('interval-component', 'n_intervals')])
def update_hip(n):
    global y_axis_hip, x_axis_hip, data
    try:
        hip_values = np.array(data['hip'])
        if len(hip_values) != len(exponentiation):
            temp_y = 0
        else:
            temp_y = np.dot(hip_values, exponentiation)
        
        temp_x = x_axis_hip[-1] + 1
        if len(x_axis_hip) > 200:
            x_axis_hip.pop(0)
            y_axis_hip.pop(0)
            
        x_axis_hip.append(temp_x)
        y_axis_hip.append(temp_y)
        
        fig = go.Figure()
        fig.update_layout(title="Hip Joint", xaxis_title="Frame", yaxis_title="Value", yaxis_range=[0.5, 1.5], plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF')
        fig.add_trace(go.Scatter(x=x_axis_hip, y=y_axis_hip, mode='lines+markers', name='hip', line=dict(color='black', width=3)))
        return fig
    except Exception as e:
        print("Error in hip callback:", e)
        return go.Figure()

# Callback for updating the Ankle graph
@app.callback(Output('ankle-graph', 'figure'), [Input('interval-component', 'n_intervals')])
def update_ankle(n):
    global y_axis_ankle, x_axis_ankle, data
    ankle_values = np.array(data['ankle'])
    if len(ankle_values) != len(exponentiation):
        temp_y = 0
    else:
        temp_y = np.dot(ankle_values, exponentiation)
        
    temp_x = x_axis_ankle[-1] + 1
    if len(x_axis_ankle) > 200:
        x_axis_ankle.pop(0)
        y_axis_ankle.pop(0)
        
    x_axis_ankle.append(temp_x)
    y_axis_ankle.append(temp_y)
    
    fig = go.Figure()
    fig.update_layout(title="Ankle Joint", xaxis_title="Frame", yaxis_title="Value", yaxis_range=[0.5, 1.5], plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF')
    fig.add_trace(go.Scatter(x=x_axis_ankle, y=y_axis_ankle, mode='lines+markers', name='ankle', line=dict(color='green', width=3)))
    return fig

# Callback for updating the Knee-Y graph (this callback was missing)
@app.callback(Output('knee-y-graph', 'figure'), [Input('interval-component', 'n_intervals')])
def update_kneey(n):
    global y_axis_kneey, x_axis_kneey, data
    knee_y_values = np.array(data['knee-y'])
    if len(knee_y_values) != len(exponentiation):
        temp_y = 0
    else:
        temp_y = np.dot(knee_y_values, exponentiation)
        
    temp_x = x_axis_kneey[-1] + 1
    if len(x_axis_kneey) > 200:
        x_axis_kneey.pop(0)
        y_axis_kneey.pop(0)
        
    x_axis_kneey.append(temp_x)
    y_axis_kneey.append(temp_y)
    
    fig = go.Figure()
    fig.update_layout(title="Knee-Y Joint", xaxis_title="Frame", yaxis_title="Value", yaxis_range=[0.5, 1.5], plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF')
    fig.add_trace(go.Scatter(x=x_axis_kneey, y=y_axis_kneey, mode='lines+markers', name='knee-y', line=dict(color='black', width=3)))
    return fig


if __name__ == '__main__':
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")
    
    Timer(1, open_browser).start()
    app.run_server(debug=True, use_reloader=False)
