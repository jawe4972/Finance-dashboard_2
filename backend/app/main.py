from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

from . import models, schemas, crud, forecasting, alerts
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance Dashboard API",
             description="API for expense tracking and predictive analytics",
             version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, 
                      db: Session = Depends(get_db),
                      token: str = Depends(oauth2_scheme)):
    return crud.create_transaction(db=db, transaction=transaction)

@app.get("/transactions/", response_model=List[schemas.Transaction])
def read_transactions(skip: int = 0, limit: int = 100,
                     db: Session = Depends(get_db),
                     token: str = Depends(oauth2_scheme)):
    transactions = crud.get_transactions(db, skip=skip, limit=limit)
    return transactions

@app.get("/transactions/{user_id}", response_model=List[schemas.Transaction])
def read_user_transactions(user_id: int, 
                          start_date: str = None,
                          end_date: str = None,
                          category: str = None,
                          db: Session = Depends(get_db),
                          token: str = Depends(oauth2_scheme)):
    return crud.get_user_transactions(
        db, user_id=user_id, 
        start_date=start_date,
        end_date=end_date,
        category=category
    )

@app.post("/forecast/", response_model=schemas.ForecastResult)
def generate_forecast(forecast_request: schemas.ForecastRequest,
                     db: Session = Depends(get_db),
                     token: str = Depends(oauth2_scheme)):
    # Get historical data
    transactions = crud.get_user_transactions(
        db, user_id=forecast_request.user_id,
        start_date=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d')
    )
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'ds': t.date,
        'y': t.amount,
        'category': t.category
    } for t in transactions])
    
    # Generate forecast
    if forecast_request.model_type == "prophet":
        forecast_df, model = forecasting.prophet_forecast(df, forecast_request.days)
    else:
        forecast_df, model = forecasting.linear_regression_forecast(df, forecast_request.days)
    
    # Check for alerts
    alert_status = alerts.check_for_alerts(
        forecast_df, 
        forecast_request.user_id,
        forecast_request.alert_thresholds
    )
    
    return {
        "forecast": forecast_df.to_dict(orient='records'),
        "model_metrics": model.metrics if hasattr(model, 'metrics') else {},
        "alerts": alert_status
    }

@app.get("/spending-analysis/{user_id}", response_model=schemas.SpendingAnalysis)
def get_spending_analysis(user_id: int,
                         period: str = "monthly",
                         db: Session = Depends(get_db),
                         token: str = Depends(oauth2_scheme)):
    return crud.get_spending_analysis(db, user_id=user_id, period=period)
