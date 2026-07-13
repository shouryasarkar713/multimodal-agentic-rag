from typing import List, Dict, Any, Optional
from app.models.db import Chunk
from app.services.parsing import PageContent, ExtractedTable, ExtractedFigure
from langchain_text_splitters import RecursiveCharacterTextSplitter

def is_overlapping(block_bbox: tuple, table_bbox: Dict[str, float]) -> bool:
    """Check if the center of a text block falls inside a table bounding box."""
    bx0, by0, bx1, by1 = block_bbox
    tx0, ty0, tx1, ty1 = table_bbox["x0"], table_bbox["y0"], table_bbox["x1"], table_bbox["y1"]
    
    bx_center = (bx0 + bx1) / 2
    by_center = (by0 + by1) / 2
    
    return (tx0 <= bx_center <= tx1) and (ty0 <= by_center <= ty1)

def chunk_text(pages: List[PageContent], tables: List[ExtractedTable]) -> List[Chunk]:
    """Recursively chunk page text, excluding table regions, respecting section boundaries."""
    chunks = []
    
    # Recursive splitter from tech stack: 800 tokens = ~3200 characters
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3200,
        chunk_overlap=800,
        separators=["\n\n", "\n", ". ", " "]
    )
    
    chunk_idx = 0
    for page in pages:
        page_num = page.page_number
        page_tables = [t for t in tables if t.page_number == page_num]
        
        # Filter out blocks that fall within table boundaries
        filtered_blocks = []
        if page.blocks:
            for block in page.blocks:
                overlap = False
                for t in page_tables:
                    if is_overlapping(block["bbox"], t.bbox):
                        overlap = True
                        break
                if not overlap:
                    filtered_blocks.append(block)
        else:
            # Fallback if no block data
            pass
            
        # Group blocks by their detected section heading
        sections_data = {}
        for section in page.sections:
            sections_data[section["title"]] = []
            
        for block in filtered_blocks:
            block_center_char = (block["start_char"] + block["end_char"]) / 2
            matched_section = "Introduction"
            for section in page.sections:
                if section["start_char"] <= block_center_char <= section["end_char"]:
                    matched_section = section["title"]
                    break
            sections_data[matched_section].append(block["text"])
            
        # Chunk text within each section separately (never split across sections)
        for section_title, blocks_text in sections_data.items():
            section_text = "\n\n".join(blocks_text).strip()
            if not section_text:
                continue
                
            split_texts = text_splitter.split_text(section_text)
            for split_text in split_texts:
                token_count = len(split_text) // 4
                
                chunk = Chunk(
                    content_type="text",
                    content_text=split_text,
                    content_markdown=None,
                    page_number=page_num,
                    chunk_index=chunk_idx,
                    section_title=section_title,
                    token_count=token_count
                )
                chunks.append(chunk)
                chunk_idx += 1
                
    return chunks

def chunk_tables(tables: List[ExtractedTable]) -> List[Chunk]:
    """Convert extracted tables into chunks. Split by rows if exceeding 2000 tokens."""
    chunks = []
    chunk_idx = 0
    
    for t in tables:
        markdown = t.markdown
        token_count = len(markdown) // 4
        
        # Table under token limit: keep as single chunk
        if token_count <= 2000:
            chunk = Chunk(
                content_type="table",
                content_text=markdown,
                content_markdown=markdown,
                page_number=t.page_number,
                chunk_index=chunk_idx,
                section_title=t.section_title,
                bbox_json=t.bbox,
                token_count=token_count
            )
            chunks.append(chunk)
            chunk_idx += 1
        else:
            # Table exceeds 2000 tokens: split by rows and duplicate headers
            lines = markdown.strip().split("\n")
            if len(lines) <= 2:
                # No data rows, just save as-is
                chunk = Chunk(
                    content_type="table",
                    content_text=markdown,
                    content_markdown=markdown,
                    page_number=t.page_number,
                    chunk_index=chunk_idx,
                    section_title=t.section_title,
                    bbox_json=t.bbox,
                    token_count=token_count
                )
                chunks.append(chunk)
                chunk_idx += 1
                continue
                
            header = lines[0]
            divider = lines[1]
            data_rows = lines[2:]
            
            half_idx = len(data_rows) // 2
            part1_rows = data_rows[:half_idx]
            part2_rows = data_rows[half_idx:]
            
            part1_md = f"{header}\n{divider}\n" + "\n".join(part1_rows)
            part2_md = f"{header}\n{divider}\n" + "\n".join(part2_rows)
            
            # Chunk 1
            chunk1 = Chunk(
                content_type="table",
                content_text=part1_md,
                content_markdown=part1_md,
                page_number=t.page_number,
                chunk_index=chunk_idx,
                section_title=t.section_title,
                bbox_json=t.bbox,
                token_count=len(part1_md) // 4
            )
            chunks.append(chunk1)
            chunk_idx += 1
            
            # Chunk 2
            chunk2 = Chunk(
                content_type="table",
                content_text=part2_md,
                content_markdown=part2_md,
                page_number=t.page_number,
                chunk_index=chunk_idx,
                section_title=t.section_title,
                bbox_json=t.bbox,
                token_count=len(part2_md) // 4
            )
            chunks.append(chunk2)
            chunk_idx += 1
            
    return chunks

def create_image_chunks(figures: List[ExtractedFigure]) -> List[Chunk]:
    """Convert extracted figures into image chunks."""
    chunks = []
    chunk_idx = 0
    
    for f in figures:
        caption = f.caption or ""
        token_count = len(caption) // 4
        
        chunk = Chunk(
            content_type="image",
            content_text=caption,
            content_markdown=None,
            page_number=f.page_number,
            chunk_index=chunk_idx,
            section_title=f.section_title,
            bbox_json=f.bbox,
            image_path=f.image_path,
            token_count=token_count
        )
        chunks.append(chunk)
        chunk_idx += 1
        
    return chunks
