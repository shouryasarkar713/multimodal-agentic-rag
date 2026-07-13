import base64
import io
from PIL import Image

def resize_and_encode_image(image_path: str, max_size: int = 512) -> str:
    """Resize image to max_size on the longest edge, and return base64 encoded string."""
    img = Image.open(image_path)
    w, h = img.size
    
    # Resize keeping aspect ratio if longest edge > max_size
    if w > max_size or h > max_size:
        if w > h:
            new_w = max_size
            new_h = int(h * (max_size / w))
        else:
            new_h = max_size
            new_w = int(w * (max_size / h))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
    # Convert image to PNG bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    
    # Base64 encode
    return base64.b64encode(img_bytes).decode("utf-8")
