# routes/strategy_routes.py

from fastapi import APIRouter
from pydantic import BaseModel
from services.strategy_service import evaluate_strategy

router = APIRouter(prefix="/bot", tags=["Trading Bot"])

class StrategyInput(BaseModel):
    price: float
    resistance: float
    support: float
    short_ma: float
    long_ma: float
    rsi: float

@router.post("/strategy")
def strategy_endpoint(data: StrategyInput):
    decision = evaluate_strategy(data.dict())
    return {"decision": decision}

