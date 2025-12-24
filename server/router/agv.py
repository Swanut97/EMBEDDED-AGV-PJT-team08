from fastapi import APIRouter
from services.agv_service import AGVService

router = APIRouter(
    prefix="/agv",
    tags=["AGV Control"]
)

agv_service = AGVService()

@router.post("/start")
async def start_tracking():
    """YOLO 탐지 및 자율 주행 시작"""
    return agv_service.start()

@router.post("/stop")
async def stop_tracking():
    """작동 중지"""
    return agv_service.stop()

@router.get("/status")
async def get_status():
    """현재 상태 확인"""
    return {
        "is_running": agv_service.is_running,
        "message": agv_service.status_message
    }