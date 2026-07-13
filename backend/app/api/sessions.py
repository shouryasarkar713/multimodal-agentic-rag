from fastapi import APIRouter, Depends
from app.dependencies import verify_api_key

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(verify_api_key)])
