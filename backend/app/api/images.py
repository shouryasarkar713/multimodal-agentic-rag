import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/{filename}", response_class=FileResponse)
async def get_image(filename: str):
    """Serve an extracted figure image file statically from /data/images/."""
    image_path = f"/data/images/{filename}"
    
    # Validate path to prevent directory traversal
    real_path = os.path.realpath(image_path)
    if not real_path.startswith("/data/images"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image path"
        )
        
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
        
    return FileResponse(image_path, media_type="image/png")
