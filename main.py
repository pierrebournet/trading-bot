

from fastapi import FastAPI
from routes.strategy_routes import router as strategy_router

app = FastAPI(title="Trading Bot Backend")

app.include_router(strategy_router)



