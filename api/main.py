"""
FastAPI REST API for FX Rate Monitoring System

Provides endpoints to:
- Query current and historical rates
- Manage alerts
- Check system health
"""

import os
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import common utilities
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.database import get_db_session, FXRate, UserAlert, AlertHistory
from common.redis_client import get_redis_client


# Initialize FastAPI app
app = FastAPI(
    title="FX Rate Monitor API",
    description="Real-time Foreign Exchange Rate Monitoring and Alert System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class RateResponse(BaseModel):
    """Response model for current rate data."""
    pair: str = Field(..., description="Currency pair (e.g., USD/EUR)")
    rate: float = Field(..., description="Current exchange rate")
    volatility: Optional[float] = Field(None, description="Rate volatility (standard deviation)")
    timestamp: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pair": "USD/EUR",
                "rate": 0.8470,
                "volatility": 0.001234,
                "timestamp": "2026-02-04T20:35:24Z"
            }
        }


class HistoricalRateResponse(BaseModel):
    """Response model for historical rate data."""
    timestamp: datetime = Field(..., description="Rate timestamp")
    rate: float = Field(..., description="Exchange rate at that time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-02-04T20:35:24",
                "rate": 0.8470
            }
        }


class AlertCreateRequest(BaseModel):
    """Request model for creating a new alert."""
    pair: str = Field(..., description="Currency pair to monitor (e.g., USD/EUR)")
    condition: str = Field(..., description="Alert condition: 'above' or 'below'")
    threshold: float = Field(..., description="Threshold value to trigger alert")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pair": "USD/EUR",
                "condition": "above",
                "threshold": 0.9000
            }
        }


class AlertResponse(BaseModel):
    """Response model for alert data."""
    id: int = Field(..., description="Alert ID")
    pair: str = Field(..., description="Currency pair")
    condition: str = Field(..., description="Alert condition: 'above' or 'below'")
    threshold: float = Field(..., description="Threshold value")
    active: bool = Field(..., description="Whether alert is active")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "pair": "USD/EUR",
                "condition": "above",
                "threshold": 0.9000,
                "active": True,
                "created_at": "2026-02-04T20:35:24"
            }
        }


class AlertHistoryResponse(BaseModel):
    """Response model for alert history."""
    id: int = Field(..., description="History record ID")
    alert_id: int = Field(..., description="Associated alert ID")
    pair: str = Field(..., description="Currency pair")
    rate: float = Field(..., description="Rate that triggered the alert")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(..., description="When alert was triggered")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "alert_id": 1,
                "pair": "USD/EUR",
                "rate": 0.9050,
                "message": "USD/EUR went above 0.9000 (current: 0.9050)",
                "triggered_at": "2026-02-04T20:35:24"
            }
        }


@app.get("/", tags=["Info"])
async def root():
    """
    Root endpoint - API information and available endpoints.
    
    Returns:
        dict: API metadata and endpoint list
    """
    return {
        "name": "FX Rate Monitor API",
        "version": "1.0.0",
        "description": "Real-time FX rate monitoring with alerts",
        "endpoints": {
            "docs": "/docs",
            "rates": {
                "current": "GET /rates",
                "history": "GET /rates/{pair}/history"
            },
            "alerts": {
                "list": "GET /alerts",
                "create": "POST /alerts",
                "delete": "DELETE /alerts/{alert_id}",
                "history": "GET /alerts/history"
            },
            "system": {
                "health": "GET /health"
            }
        },
        "status": "operational"
    }


@app.get("/rates", response_model=List[RateResponse], tags=["Rates"])
async def get_current_rates():
    """
    Get all current exchange rates from Redis cache.
    
    Returns current rates for all tracked currency pairs along with
    their volatility (if calculated).
    
    Returns:
        List[RateResponse]: List of current rates with volatility
        
    Raises:
        HTTPException: If Redis connection fails
    """
    try:
        redis_client = get_redis_client()
        
        # Get all current rates from Redis
        all_rates = redis_client.get_all_current_rates()
        
        if not all_rates:
            return []
        
        # Build response with rates and volatility
        rates_response = []
        
        for pair, rate in all_rates.items():
            # Get volatility for this pair
            volatility = redis_client.get_volatility(pair)
            
            rate_data = RateResponse(
                pair=pair,
                rate=rate,
                volatility=volatility,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            rates_response.append(rate_data)
        
        # Sort by pair name for consistent ordering
        rates_response.sort(key=lambda x: x.pair)
        
        return rates_response
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch rates from Redis: {str(e)}"
        )


@app.get("/rates/{pair}/history", response_model=List[HistoricalRateResponse], tags=["Rates"])
async def get_rate_history(
    pair: str,
    hours: int = Query(default=24, ge=1, le=720, description="Number of hours of history (1-720)")
):
    """
    Get historical exchange rates for a specific currency pair from database.
    
    Query PostgreSQL for time-series data of a currency pair over specified time period.
    
    Args:
        pair: Currency pair (e.g., "USD/EUR")
        hours: Number of hours of history to fetch (default: 24, max: 720/30 days)
        
    Returns:
        List[HistoricalRateResponse]: Time-series data of rates
        
    Raises:
        HTTPException: If database query fails or pair not found
    """
    try:
        session = get_db_session()
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Query database for historical rates
        rates = session.query(FXRate).filter(
            FXRate.pair == pair,
            FXRate.timestamp >= start_time,
            FXRate.timestamp <= end_time
        ).order_by(FXRate.timestamp.asc()).all()
        
        session.close()
        
        if not rates:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for pair '{pair}' in the last {hours} hours"
            )
        
        # Build response
        history_response = [
            HistoricalRateResponse(
                timestamp=rate.timestamp,
                rate=rate.rate
            )
            for rate in rates
        ]
        
        return history_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch historical data: {str(e)}"
        )


@app.post("/alerts", response_model=AlertResponse, status_code=201, tags=["Alerts"])
async def create_alert(alert_request: AlertCreateRequest):
    """
    Create a new price alert for a currency pair.
    
    Alert will be checked by the alert engine consumer and triggered when
    the condition is met (rate goes above/below threshold).
    
    Args:
        alert_request: Alert configuration (pair, condition, threshold)
        
    Returns:
        AlertResponse: Created alert with ID
        
    Raises:
        HTTPException: If validation fails or database error occurs
    """
    # Validate condition field
    if alert_request.condition not in ["above", "below"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition '{alert_request.condition}'. Must be 'above' or 'below'."
        )
    
    # Validate threshold is positive
    if alert_request.threshold <= 0:
        raise HTTPException(
            status_code=400,
            detail="Threshold must be a positive number."
        )
    
    try:
        session = get_db_session()
        
        # Create new alert
        new_alert = UserAlert(
            pair=alert_request.pair,
            condition=alert_request.condition,
            threshold=alert_request.threshold,
            active=True
        )
        
        session.add(new_alert)
        session.commit()
        session.refresh(new_alert)  # Get the generated ID
        
        # Build response
        alert_response = AlertResponse(
            id=new_alert.id,
            pair=new_alert.pair,
            condition=new_alert.condition,
            threshold=new_alert.threshold,
            active=new_alert.active,
            created_at=new_alert.created_at
        )
        
        session.close()
        
        return alert_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create alert: {str(e)}"
        )


@app.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(active_only: bool = Query(default=True, description="Return only active alerts")):
    """
    Get all alerts from database.
    
    Query parameter allows filtering for only active alerts (default)
    or all alerts including inactive ones.
    
    Args:
        active_only: If True, return only active alerts (default: True)
        
    Returns:
        List[AlertResponse]: List of alerts
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        session = get_db_session()
        
        # Query alerts
        query = session.query(UserAlert)
        
        if active_only:
            query = query.filter(UserAlert.active == True)
        
        alerts = query.order_by(UserAlert.created_at.desc()).all()
        
        session.close()
        
        # Build response
        alerts_response = [
            AlertResponse(
                id=alert.id,
                pair=alert.pair,
                condition=alert.condition,
                threshold=alert.threshold,
                active=alert.active,
                created_at=alert.created_at
            )
            for alert in alerts
        ]
        
        return alerts_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@app.delete("/alerts/{alert_id}", tags=["Alerts"])
async def delete_alert(alert_id: int):
    """
    Delete a specific alert by ID.
    
    Permanently removes the alert from the database. Alert will no longer
    be checked by the alert engine.
    
    Args:
        alert_id: ID of the alert to delete
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If alert not found or database error occurs
    """
    try:
        session = get_db_session()
        
        # Find alert
        alert = session.query(UserAlert).filter(UserAlert.id == alert_id).first()
        
        if not alert:
            session.close()
            raise HTTPException(
                status_code=404,
                detail=f"Alert with ID {alert_id} not found"
            )
        
        # Delete alert
        session.delete(alert)
        session.commit()
        session.close()
        
        return {
            "success": True,
            "message": f"Alert {alert_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete alert: {str(e)}"
        )


@app.get("/alerts/history", response_model=List[AlertHistoryResponse], tags=["Alerts"])
async def get_alert_history(limit: int = Query(default=50, ge=1, le=500, description="Number of records to return")):
    """
    Get history of triggered alerts.
    
    Returns most recent alert triggers with details about when and why
    they were triggered.
    
    Args:
        limit: Maximum number of history records to return (default: 50, max: 500)
        
    Returns:
        List[AlertHistoryResponse]: List of triggered alerts
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        session = get_db_session()
        
        # Query alert history
        history = session.query(AlertHistory).order_by(
            AlertHistory.triggered_at.desc()
        ).limit(limit).all()
        
        session.close()
        
        # Build response
        history_response = [
            AlertHistoryResponse(
                id=record.id,
                alert_id=record.alert_id,
                pair=record.pair,
                rate=record.rate,
                message=record.message,
                triggered_at=record.triggered_at
            )
            for record in history
        ]
        
        return history_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alert history: {str(e)}"
        )


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint - verifies database and Redis connectivity.
    
    Returns:
        dict: Health status of all components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # Check PostgreSQL
    try:
        session = get_db_session()
        # Simple query to check connection
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    if status_code == 503:
        raise HTTPException(status_code=status_code, detail=health_status)
    
    return health_status


if __name__ == "__main__":
    # Run the API server
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Set to True for development
        log_level="info"
    )
