from fastapi import APIRouter, Depends
from app.dependencies import verify_api_key

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(verify_api_key)])
