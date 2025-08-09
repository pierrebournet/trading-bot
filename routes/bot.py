from fastapi import APIRouter
from services.bot_controller import start_bot, stop_bot

router = APIRouter()

@router.post("/start")
def start():
    return start_bot()

@router.post("/stop")
def stop():
    return stop_bot()
