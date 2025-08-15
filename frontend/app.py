import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# API configuration
API_BASE_URL = "http://localhost:8000"
DEFAULT_USER_ID = 1  # For demo purposes

# Layout
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Personal Finance Dashboard", className="text-center my-4"))),
    
    dbc.Tabs([
        dbc.Tab(label="Overview", children=[
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id='daily-spending-chart'),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=(datetime.now() - timedelta(days=365)).date,
                        max_date_allowed=datetime.now().date,
                        start_date=(datetime.now() - timedelta(days=30)).date,
                        end_date=datetime.now().date
                    )
                ], width=8),
                dbc.Col([
                    dcc.Graph(id='category-pie'),
                    html.Div(id='alerts-container', className="mt-3")
                ], width=4)
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='forecast-chart'), width=12)
            ])
        ]),
        
        dbc.Tab(label="Detailed Analysis", children=[
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id='category-selector',
                        multi=True,
                        placeholder="Select categories"
                    ),
                    dcc.Graph(id='category-trend-chart')
                ], width=8),
                dbc.Col([
                    dcc.Graph(id='weekday-heatmap'),
                    dcc.Graph(id='monthly-comparison')
                ], width=4)
            ])
        ]),
        
        dbc.Tab(label="Budget Settings", children=[
            dbc.Row([
                dbc.Col([
                    html.H3("Set Budget Limits"),
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
                    html.Div(id='alert-status', className="mt-3")
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
    dcc.Store(id='forecast-data')
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
    Output('daily-spending-chart', 'figure'),
    [Input('transaction-data', 'data')]
)
def update_daily_spending_chart(data):
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    fig = px.line(
        df.groupby('date')['amount'].sum().reset_index(),
        x='date', y='amount',
        title="Daily Spending Trend",
        labels={'amount': 'Amount ($)', 'date': 'Date'}
    )
    
    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=True)),
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
        return px.pie(title="No data available")
    
    category_totals = df.groupby('category')['amount'].sum().reset_index()
    
    fig = px.pie(
        category_totals,
        values='amount',
        names='category',
        title="Spending by Category"
    )
    
    return fig

@app.callback(
    Output('forecast-chart', 'figure'),
    [Input('forecast-data', 'data')]
)
def update_forecast_chart(data):
    if not data or 'forecast' not in data:
        return go.Figure()
    
    forecast_df = pd.DataFrame(data['forecast'])
    forecast_df['ds'] = pd.to_datetime(forecast_df['ds'])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'],
        y=forecast_df['yhat'],
        name="Forecast",
        line=dict(color='royalblue', width=2)
    ))
    
    if 'yhat_lower' in forecast_df.columns and 'yhat_upper' in forecast_df.columns:
        fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat_upper'],
            fill=None,
            mode='lines',
            line=dict(width=0),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat_lower'],
            fill='tonexty',
            mode='lines',
            line=dict(width=0),
            fillcolor='rgba(65, 105, 225, 0.2)',
            name="Confidence Interval"
        ))
    
    fig.update_layout(
        title="30-Day Cash Flow Forecast",
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        hovermode="x"
    )
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

