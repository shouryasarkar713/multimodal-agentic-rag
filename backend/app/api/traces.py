from fastapi import APIRouter, Depends
from app.dependencies import verify_api_key

router = APIRouter(prefix="/traces", tags=["traces"], dependencies=[Depends(verify_api_key)])
