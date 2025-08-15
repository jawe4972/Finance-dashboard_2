import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
import numpy as np

def prophet_forecast(df, days=30):
    # Prepare data
    df = df.groupby('ds')['y'].sum().reset_index()
    
    # Fit model
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='multiplicative'
    )
    model.fit(df)
    
    # Make future dataframe
    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)
    
    # Calculate metrics
    y_true = df['y'].values[-30:]  # Last 30 days for validation
    y_pred = forecast['yhat'].values[-30-days:-days]
    mae = mean_absolute_error(y_true, y_pred)
    
    model.metrics = {
        'mae': mae,
        'last_30_days_actual': y_true.tolist(),
        'last_30_days_predicted': y_pred.tolist()
    }
    
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days), model

def linear_regression_forecast(df, days=30):
    df = df.groupby('ds')['y'].sum().reset_index()
    df['ds'] = pd.to_datetime(df['ds'])
    df['days_since_start'] = (df['ds'] - df['ds'].min()).dt.days
    
    # Create lag features
    for i in [1, 7, 30]:
        df[f'lag_{i}'] = df['y'].shift(i)
    
    df = df.dropna()
    
    # Split data
    X = df[['days_since_start', 'lag_1', 'lag_7', 'lag_30']]
    y = df['y']
    
    # Train model
    model = LinearRegression()
    model.fit(X, y)
    
    # Generate future dates
    last_date = df['ds'].max()
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=days
    )
    
    # Prepare future features
    future_df = pd.DataFrame({'ds': future_dates})
    future_df['days_since_start'] = (future_df['ds'] - df['ds'].min()).dt.days
    
    for i in [1, 7, 30]:
        future_df[f'lag_{i}'] = df['y'].shift(i).values[-days:]
    
    # Predict
    future_df['yhat'] = model.predict(future_df[['days_since_start', 'lag_1', 'lag_7', 'lag_30']])
    
    # Calculate metrics
    y_true = df['y'].values[-30:]
    y_pred = model.predict(X[-30:])
    mae = mean_absolute_error(y_true, y_pred)
    
    model.metrics = {
        'mae': mae,
        'last_30_days_actual': y_true.tolist(),
        'last_30_days_predicted': y_pred.tolist()
    }
    
    return future_df[['ds', 'yhat']], model

