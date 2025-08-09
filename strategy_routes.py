# routes/strategy_routes.py

from fastapi import APIRouter
from services.strategy_service import analyze_strategy

router = APIRouter()

@router.post("/bot/strategy")
def get_strategy_decision(data: dict):
    return analyze_strategy(data)
