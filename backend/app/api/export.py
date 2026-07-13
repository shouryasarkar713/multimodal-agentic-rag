import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, verify_api_key
from app.models.db import Message

router = APIRouter(prefix="/export", tags=["export"], dependencies=[Depends(verify_api_key)])

class ExportRequest(BaseModel):
    message_id: uuid.UUID

@router.post("/markdown", status_code=status.HTTP_200_OK)
async def export_markdown(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Export an assistant reply message as a formatted markdown document download."""
    message = await db.get(Message, body.message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
        
    if message.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only assistant messages can be exported."
        )
        
    md_lines = []
    md_lines.append("# Answer")
    md_lines.append(message.content)
    md_lines.append("")
    
    if message.citations:
        md_lines.append("## Citations")
        for idx, cit in enumerate(message.citations):
            title = cit.get("document_title") or "Unknown Document"
            page = cit.get("page_number", 1)
            sec = cit.get("section_title") or "General"
            excerpt = cit.get("excerpt") or ""
            md_lines.append(f"{idx + 1}. **{title}**, Page {page}, Section: {sec}")
            md_lines.append(f"> {excerpt}")
            md_lines.append("")
            
    if message.figure_refs:
        md_lines.append("## Figures Referenced")
        for fig in message.figure_refs:
            title = fig.get("caption") or "Figure"
            page = fig.get("page_number", 1)
            doc_title = fig.get("document_title") or "Document"
            md_lines.append(f"- Figure from \"{doc_title}\", Page {page}: {title}")
            
    markdown_text = "\n".join(md_lines)
    
    return Response(
        content=markdown_text,
        media_type="text/markdown",
        headers={
            "Content-Disposition": 'attachment; filename="answer_export.md"'
        }
    )
