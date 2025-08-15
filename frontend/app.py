import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta
import json

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# API configuration
API_BASE_URL = "http://localhost:8000"
DEFAULT_USER_ID = 1  # For demo purposes

# Layout
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Personal Finance Dashboard", className="text-center my-4"))),
    
    dbc.Tabs([
        dbc.Tab(label="Financial Overview", children=[
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='daily-spending-chart'),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=(datetime.now() - timedelta(days=365)).date(),
                        max_date_allowed=datetime.now().date(),
                        start_date=(datetime.now() - timedelta(days=30)).date(),
                        end_date=datetime.now().date()
                    )
                ], width=8),
                dbc.Col([
                    dcc.Graph(id='category-pie'),
                    html.Div(id='alerts-container', className="mt-3 alert alert-warning")
                ], width=4)
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='forecast-chart'), width=12)
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='forecast-components'), width=12)
            ])
        ]),
        
        dbc.Tab(label="Detailed Analysis", children=[
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id='category-selector',
                        options=[],
                        multi=True,
                        placeholder="Select categories"
                    ),
                    dcc.Graph(id='category-trend-chart')
                ], width=8),
                dbc.Col([
                    dcc.Graph(id='weekday-heatmap'),
                    dcc.RadioItems(
                        id='period-selector',
                        options=[
                            {'label': 'Daily', 'value': 'daily'},
                            {'label': 'Weekly', 'value': 'weekly'},
                            {'label': 'Monthly', 'value': 'monthly'}
                        ],
                        value='monthly',
                        inline=True
                    ),
                    dcc.Graph(id='period-comparison')
                ], width=4)
            ])
        ]),
        
        dbc.Tab(label="Budget & Alerts", children=[
            dbc.Row([
                dbc.Col([
                    html.H3("Budget Settings"),
                    dash_table.DataTable(
                        id='budget-table',
                        columns=[
                            {'name': 'Category', 'id': 'category'},
                            {'name': 'Monthly Budget', 'id': 'budget'},
                            {'name': 'Alert Threshold', 'id': 'threshold'}
                        ],
                        data=[],
                        editable=True
                    ),
                    dbc.Button("Save Budget", id='save-budget', className="mt-3")
                ], width=6),
                dbc.Col([
                    html.H3("Alert Preferences"),
                    dcc.Checklist(
                        id='alert-preferences',
                        options=[
                            {'label': 'Email Alerts', 'value': 'email'},
                            {'label': 'SMS Alerts', 'value': 'sms'}
                        ],
                        value=['email']
                    ),
                    html.Div(id='alert-status', className="mt-3 alert alert-info")
                ], width=6)
            ])
        ])
    ]),
    
    dcc.Interval(
        id='interval-component',
        interval=60*60*1000,  # 1 hour
        n_intervals=0
    ),
    dcc.Store(id='transaction-data'),
    dcc.Store(id='forecast-data'),
    dcc.Store(id='analysis-data')
], fluid=True)

# Callbacks
@app.callback(
    Output('transaction-data', 'data'),
    [Input('date-range', 'start_date'),
     Input('date-range', 'end_date')]
)
def update_transaction_data(start_date, end_date):
    response = requests.get(
        f"{API_BASE_URL}/transactions/{DEFAULT_USER_ID}",
        params={
            'start_date': start_date,
            'end_date': end_date
        }
    )
    return response.json()

@app.callback(
    Output('forecast-data', 'data'),
    [Input('interval-component', 'n_intervals')]
)
def update_forecast_data(n):
    response = requests.post(
        f"{API_BASE_URL}/forecast/",
        json={
            "user_id": DEFAULT_USER_ID,
            "model_type": "prophet",
            "days": 30,
            "alert_thresholds": {
                "daily_spending": 200,
                "weekly_spending": 1000,
                "negative_balance": True
            }
        }
    )
    return response.json()

@app.callback(
    Output('analysis-data', 'data'),
    [Input('interval-component', 'n_intervals')]
)
def update_analysis_data(n):
    response = requests.get(
        f"{API_BASE_URL}/transactions/analysis/{DEFAULT_USER_ID}",
        params={"period": "monthly"}
    )
    return response.json()

@app.callback(
    Output('daily-spending-chart', 'figure'),
    [Input('transaction-data', 'data')]
)
def update_daily_spending_chart(data):
    df = pd.DataFrame(data)
    if len(df) == 0:
        return go.Figure()
    
    df['date'] = pd.to_datetime(df['date'])
    daily_df = df.groupby('date')['amount'].sum().reset_index()
    
    fig = go.Figure(
        go.Scatter(
            x=daily_df['date'],
            y=daily_df['amount'],
            mode='lines+markers',
            name="Daily Spending"
        )
    )
    
    fig.update_layout(
        title="Daily Spending Trend",
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        hovermode="x unified"
    )
    
    return fig

@app.callback(
    Output('category-pie', 'figure'),
    [Input('transaction-data', 'data')]
)
def update_category_pie(data):
    df = pd.DataFrame(data)
    if len(df) == 0:
        return go.Figure()
    
    category_df = df.groupby('category')['amount'].sum().reset_index()
    
    fig = go.Figure(
        go.Pie(
            labels=category_df['category'],
            values=category_df['amount'],
            hole=0.3,
            textinfo='label+percent'
        )
    )
    
    fig.update_layout(title="Spending by Category")
    return fig

@app.callback(
    [Output('forecast-chart', 'figure'),
     Output('forecast-components', 'figure'),
     Output('alerts-container', 'children')],
    [Input('forecast-data', 'data')]
)
def update_forecast_charts(data):
    if not data or 'forecast' not in data:
        return go.Figure(), go.Figure(), "No forecast data available"
    
    # Main forecast chart
    forecast_fig = go.Figure(data['visualizations']['forecast_plot'])
    
    # Components chart
    components_fig = go.Figure(data['visualizations']['components_plot']) if data['visualizations']['components_plot'] else go.Figure()
    
    # Alerts
    alerts = []
    if data.get('alerts', {}).get('potential_issues'):
        alerts.append(html.H4("Alerts:"))
        for alert in data['alerts']['potential_issues']:
            alerts.append(html.P(alert, className="alert alert-danger"))
    
    return forecast_fig, components_fig, alerts

@app.callback(
    [Output('weekday-heatmap', 'figure'),
     Output('period-comparison', 'figure'),
     Output('category-selector', 'options')],
    [Input('analysis-data', 'data'),
     Input('period-selector', 'value')]
)
def update_analysis_charts(data, period):
    if not data:
        return go.Figure(), go.Figure(), []
    
    # Heatmap
    heatmap_fig = go.Figure(data['heatmap'])
    
    # Period comparison
    period_fig = go.Figure(data['period_analysis'])
    period_fig.update_layout(title=f"Spending by {period.capitalize()}")
    
    # Category options
    category_options = [
        {'label': cat, 'value': cat} 
        for cat in pd.DataFrame(data['category_breakdown']['data'][0]['labels']).tolist()
    ]
    
    return heatmap_fig, period_fig, category_options

@app.callback(
    Output('category-trend-chart', 'figure'),
    [Input('transaction-data', 'data'),
     Input('category-selector', 'value')]
)
def update_category_trend(data, selected_categories):
    df = pd.DataFrame(data)
    if len(df) == 0 or not selected_categories:
        return go.Figure()
    
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[df['category'].isin(selected_categories)]
    
    fig = go.Figure()
    for category in selected_categories:
        category_df = filtered_df[filtered_df['category'] == category]
        daily_df = category_df.groupby('date')['amount'].sum().reset_index()
        
        fig.add_trace(go.Scatter(
            x=daily_df['date'],
            y=daily_df['amount'],
            mode='lines',
            name=category
        ))
    
    fig.update_layout(
        title="Category Spending Trends",
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        hovermode="x unified"
    )
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
