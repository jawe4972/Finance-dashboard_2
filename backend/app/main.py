from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import logging

from . import models, schemas, crud, forecasting, alerts, visualization
from .database import SessionLocal, engine

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal Finance Dashboard API",
    description="API for expense tracking and predictive analytics",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction record"""
    try:
        return crud.create_transaction(db=db, transaction=transaction)
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/transactions/", response_model=List[schemas.Transaction])
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get paginated list of transactions"""
    return crud.get_transactions(db, skip=skip, limit=limit)

@app.get("/transactions/analysis/{user_id}", response_model=schemas.SpendingAnalysis)
def get_spending_analysis(
    user_id: int,
    period: str = "monthly",
    db: Session = Depends(get_db)
):
    """Get spending analysis by category and period"""
    return visualization.get_spending_analysis(db, user_id, period)

@app.post("/forecast/", response_model=schemas.ForecastResult)
def generate_forecast(forecast_request: schemas.ForecastRequest, db: Session = Depends(get_db)):
    """Generate cash flow forecast with alerts"""
    try:
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
        
        # Generate alerts
        alert_status = alerts.check_for_alerts(
            forecast_df, 
            forecast_request.user_id,
            forecast_request.alert_thresholds
        )
        
        return {
            "forecast": forecast_df.to_dict(orient='records'),
            "model_metrics": model.metrics if hasattr(model, 'metrics') else {},
            "alerts": alert_status,
            "visualizations": visualization.generate_forecast_plots(forecast_df, model)
        }
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

