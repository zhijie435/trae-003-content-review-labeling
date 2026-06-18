from fastapi import APIRouter

from . import tasks, inspections, sampling, statistics

api_router = APIRouter()
api_router.include_router(tasks.router)
api_router.include_router(inspections.router)
api_router.include_router(sampling.router)
api_router.include_router(statistics.router)
