import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def generate_forecast_plots(forecast_df: pd.DataFrame, model) -> Dict[str, Any]:
    """Generate visualization data for forecast results"""
    try:
        forecast_df['ds'] = pd.to_datetime(forecast_df['ds'])
        
        # Main forecast plot
        forecast_fig = go.Figure()
        forecast_fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat'],
            name="Forecast",
            line=dict(color='royalblue', width=2)
        ))
        
        if 'yhat_lower' in forecast_df.columns and 'yhat_upper' in forecast_df.columns:
            forecast_fig.add_trace(go.Scatter(
                x=forecast_df['ds'],
                y=forecast_df['yhat_upper'],
                fill=None,
                mode='lines',
                line=dict(width=0),
                showlegend=False
            ))
            forecast_fig.add_trace(go.Scatter(
                x=forecast_df['ds'],
                y=forecast_df['yhat_lower'],
                fill='tonexty',
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(65, 105, 225, 0.2)',
                name="Confidence Interval"
            ))
        
        forecast_fig.update_layout(
            title="30-Day Cash Flow Forecast",
            xaxis_title="Date",
            yaxis_title="Amount ($)",
            hovermode="x"
        )
        
        # Model components plot (for Prophet only)
        components_fig = None
        if hasattr(model, 'plot_components'):
            components_fig = model.plot_components(forecast_df)
            components_fig = go.Figure(components_fig)
            components_fig.update_layout(title="Forecast Components")
        
        return {
            "forecast_plot": forecast_fig.to_dict(),
            "components_plot": components_fig.to_dict() if components_fig else None
        }
    except Exception as e:
        logger.error(f"Visualization error: {str(e)}")
        raise

def get_spending_analysis(db, user_id: int, period: str = "monthly"):
    """Generate spending analysis visualizations"""
    try:
        # Get transactions from database
        transactions = crud.get_user_transactions(db, user_id=user_id)
        df = pd.DataFrame([{
            'date': t.date,
            'amount': t.amount,
            'category': t.category
        } for t in transactions])
        
        df['date'] = pd.to_datetime(df['date'])
        
        # Category breakdown
        category_df = df.groupby('category')['amount'].sum().reset_index()
        category_fig = go.Figure(go.Pie(
            labels=category_df['category'],
            values=category_df['amount'],
            hole=0.3
        ))
        category_fig.update_layout(title="Spending by Category")
        
        # Time period analysis
        if period == "monthly":
            df['period'] = df['date'].dt.to_period('M')
        elif period == "weekly":
            df['period'] = df['date'].dt.to_period('W')
        else:
            df['period'] = df['date'].dt.date
        
        period_df = df.groupby('period')['amount'].sum().reset_index()
        period_df['period'] = period_df['period'].astype(str)
        
        period_fig = go.Figure(go.Bar(
            x=period_df['period'],
            y=period_df['amount'],
            marker_color='indianred'
        ))
        period_fig.update_layout(
            title=f"Spending by {period.capitalize()}",
            xaxis_title=period.capitalize(),
            yaxis_title="Amount ($)"
        )
        
        # Weekday heatmap
        df['weekday'] = df['date'].dt.day_name()
        df['hour'] = df['date'].dt.hour
        heatmap_df = df.groupby(['weekday', 'hour'])['amount'].sum().unstack()
        
        heatmap_fig = go.Figure(go.Heatmap(
            x=heatmap_df.columns,
            y=heatmap_df.index,
            z=heatmap_df.values,
            colorscale='Viridis'
        ))
        heatmap_fig.update_layout(
            title="Spending Heatmap by Weekday/Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Weekday"
        )
        
        return {
            "category_breakdown": category_fig.to_dict(),
            "period_analysis": period_fig.to_dict(),
            "heatmap": heatmap_fig.to_dict()
        }
    except Exception as e:
        logger.error(f"Spending analysis error: {str(e)}")
        raise
