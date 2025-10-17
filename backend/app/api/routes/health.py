"""
Health check endpoints
"""
import torch
from datetime import datetime
from fastapi import APIRouter, Request
from app.models.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request):
    """
    Health check endpoint
    
    Returns:
        Health status including model readiness and GPU availability
    """
    model_manager = request.app.state.model_manager
    
    return HealthCheckResponse(
        status="healthy" if model_manager.is_ready() else "initializing",
        version="1.0.0",
        models_loaded=model_manager.is_ready(),
        gpu_available=torch.cuda.is_available(),
        timestamp=datetime.now()
    )


@router.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check for load balancers
    
    Returns:
        200 if ready, 503 if not ready
    """
    model_manager = request.app.state.model_manager
    
    if model_manager.is_ready():
        return {"status": "ready"}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")
