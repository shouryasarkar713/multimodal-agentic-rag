import os
import re
import fitz  # PyMuPDF
import pdfplumber
import logging
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class PageContent:
    page_number: int  # 1-indexed
    full_text: str
    sections: List[Dict[str, Any]]  # [{"title": "Introduction", "start_char": 0, "end_char": 500}, ...]
    blocks: Optional[List[Dict[str, Any]]] = None

@dataclass
class ExtractedTable:
    page_number: int
    markdown: str
    bbox: Dict[str, float]  # {"x0": float, "y0": float, "x1": float, "y1": float}
    section_title: Optional[str]

@dataclass
class ExtractedFigure:
    page_number: int
    image_path: str  # Relative path in /data/images/
    bbox: Dict[str, float]
    caption: Optional[str]
    section_title: Optional[str]

def extract_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract metadata from PDF: title, authors, total_pages."""
    logging.info(f"Extracting metadata from {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        raise ValueError("Could not open PDF. The file may be corrupted or password protected.")
    total_pages = len(doc)
    
    metadata = doc.metadata or {}
    title = metadata.get("title", "")
    
    # Fallback title: search page 1 for first line > 14pt
    if not title or title.strip() == "":
        first_page = doc[0]
        blocks = first_page.get_text("dict").get("blocks", [])
        candidate_title = ""
        found = False
        for block in blocks:
            if found:
                break
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span.get("size", 0) > 14:
                            candidate_title += span.get("text", "") + " "
                            found = True
                if candidate_title.strip():
                    break
        title = candidate_title.strip() if candidate_title.strip() else "Untitled Document"
    
    author_str = metadata.get("author", "")
    authors = None
    if author_str and author_str.strip():
        if ";" in author_str:
            authors = [a.strip() for a in author_str.split(";")]
        elif "," in author_str:
            authors = [a.strip() for a in author_str.split(",")]
        else:
            authors = [author_str.strip()]
            
    doc.close()
    return {
        "title": title,
        "authors": authors,
        "total_pages": total_pages
    }

def extract_pages(pdf_path: str) -> List[PageContent]:
    """Page-by-page text extraction with section heading detection."""
    logging.info(f"Extracting pages from {pdf_path}")
    doc = fitz.open(pdf_path)
    pages_content = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict").get("blocks", [])
        
        # Collect all font sizes to calculate median
        sizes = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span.get("text", "").strip():
                            sizes.append(span.get("size", 10.0))
                            
        median_size = statistics.median(sizes) if sizes else 10.0
        
        # Build page text while tracking character offsets of blocks
        full_text = ""
        blocks_list = []
        offset = 0
        
        for block in blocks:
            if "lines" in block:
                block_text = ""
                block_spans = []
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span.get("text", "")
                        block_spans.append(span)
                    block_text += " "
                
                block_text = block_text.strip()
                if block_text:
                    start_char = offset
                    full_text += block_text + "\n\n"
                    offset += len(block_text) + 2
                    end_char = len(full_text)
                    blocks_list.append({
                        "text": block_text,
                        "start_char": start_char,
                        "end_char": end_char,
                        "bbox": block.get("bbox", (0,0,0,0)),
                        "spans": block_spans
                    })
        
        # Detect sections on this page
        sections = []
        current_section_title = "Introduction"
        current_start = 0
        
        for b in blocks_list:
            is_heading = False
            b_spans = b["spans"]
            if b_spans:
                max_size = max(s.get("size", 0) for s in b_spans)
                is_bold = any((s.get("flags", 0) & 2) or ("bold" in s.get("font", "").lower()) for s in b_spans)
                if (max_size >= 1.3 * median_size) or (is_bold and len(b["text"]) <= 100):
                    is_heading = True
            
            if is_heading:
                if b["start_char"] > current_start:
                    sections.append({
                        "title": current_section_title,
                        "start_char": current_start,
                        "end_char": b["start_char"]
                    })
                current_section_title = b["text"]
                current_start = b["start_char"]
                
        # Append the final section
        sections.append({
            "title": current_section_title,
            "start_char": current_start,
            "end_char": len(full_text)
        })
        
        pages_content.append(PageContent(
            page_number=page_num + 1,
            full_text=full_text,
            sections=sections,
            blocks=blocks_list
        ))
        
    doc.close()
    return pages_content

def cells_to_markdown(cells: List[List[Optional[str]]]) -> str:
    """Convert list of cells to markdown table string."""
    if not cells or not cells[0]:
        return ""
    md = ""
    # Header row
    headers = [str(c or "").replace("\n", " ").strip() for c in cells[0]]
    md += "| " + " | ".join(headers) + " |\n"
    # Divider row
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    # Data rows
    for row in cells[1:]:
        row_str = [str(c or "").replace("\n", " ").strip() for c in row]
        if len(row_str) < len(headers):
            row_str += [""] * (len(headers) - len(row_str))
        md += "| " + " | ".join(row_str[:len(headers)]) + " |\n"
    return md

def extract_tables(pdf_path: str, pages_content: List[PageContent]) -> List[ExtractedTable]:
    """Extract tables using pdfplumber, match them to sections, with fallback validation."""
    logging.info(f"Extracting tables from {pdf_path}")
    extracted_tables = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            page_num = idx + 1
            # Retrieve sections for this page from PageContent list
            page_sections = []
            if idx < len(pages_content):
                page_sections = pages_content[idx].sections
            
            # Find tables on page
            tables = page.find_tables()
            for t_idx, table in enumerate(tables):
                bbox = {
                    "x0": float(table.bbox[0]),
                    "y0": float(table.bbox[1]),
                    "x1": float(table.bbox[2]),
                    "y1": float(table.bbox[3])
                }
                
                cells = table.extract()
                if not cells:
                    continue
                
                # Check for >50% None cells (Risk 1 Mitigation)
                total_cells = sum(len(row) for row in cells)
                none_cells = sum(sum(1 for c in row if c is None) for row in cells)
                if total_cells > 0 and (none_cells / total_cells) > 0.5:
                    logging.warning(f"Discarding table on page {page_num} due to >50% None cells (fallback to text).")
                    continue
                
                markdown_str = cells_to_markdown(cells)
                if not markdown_str.strip():
                    continue
                
                # Determine section table falls under based on vertical center
                y_center = (bbox["y0"] + bbox["y1"]) / 2
                section_title = "Introduction"
                
                # Retrieve text blocks to check coordinates
                # We open with PyMuPDF to get exact heading locations since pdfplumber is separate
                doc_fitz = fitz.open(pdf_path)
                page_fitz = doc_fitz[idx]
                fitz_blocks = page_fitz.get_text("dict").get("blocks", [])
                
                # Collect heading positions on this page
                headings_y = []
                # Recalculate median to filter headings correctly
                sizes = [span.get("size", 10.0) for b in fitz_blocks if "lines" in b 
                         for l in b["lines"] for span in l["spans"] if span.get("text", "").strip()]
                median_size = statistics.median(sizes) if sizes else 10.0
                
                for b in fitz_blocks:
                    if "lines" in b:
                        b_text = "".join(s.get("text", "") for l in b["lines"] for s in l["spans"]).strip()
                        b_spans = [s for l in b["lines"] for s in l["spans"]]
                        if b_text and b_spans:
                            max_size = max(s.get("size", 0) for s in b_spans)
                            is_bold = any((s.get("flags", 0) & 2) or ("bold" in s.get("font", "").lower()) for s in b_spans)
                            if (max_size >= 1.3 * median_size) or (is_bold and len(b_text) <= 100):
                                headings_y.append((b_text, b["bbox"][1]))
                                
                doc_fitz.close()
                
                # Find heading above table closest to center
                headings_above = [h for h in headings_y if h[1] < y_center]
                if headings_above:
                    headings_above.sort(key=lambda x: x[1], reverse=True)
                    section_title = headings_above[0][0]
                elif page_sections:
                    section_title = page_sections[0]["title"]
                
                extracted_tables.append(ExtractedTable(
                    page_number=page_num,
                    markdown=markdown_str,
                    bbox=bbox,
                    section_title=section_title
                ))
                
    return extracted_tables

def extract_figures(pdf_path: str, document_id: str, pages_content: List[PageContent]) -> List[ExtractedFigure]:
    """Extract figures/images from PDF, save them to disk, and extract captions."""
    logging.info(f"Extracting figures from {pdf_path}")
    extracted_figures = []
    
    os.makedirs("/data/images", exist_ok=True)
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_sections = []
        if page_num < len(pages_content):
            page_sections = pages_content[page_num].sections
            
        blocks = page.get_text("dict").get("blocks", [])
        images = page.get_images(full=True)
        
        for index, img_info in enumerate(images):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            if not base_image:
                continue
                
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            
            # Skip small decorative/logo images
            if width < 100 or height < 100:
                continue
                
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            
            # Save image
            filename = f"{document_id}_{page_num + 1}_{index}.png"
            image_path = f"/data/images/{filename}"
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
                
            # Bounding box of image on page
            rects = page.get_image_rects(xref)
            image_rect = rects[0] if rects else fitz.Rect(0, 0, 0, 0)
            bbox = {
                "x0": float(image_rect.x0),
                "y0": float(image_rect.y0),
                "x1": float(image_rect.x1),
                "y1": float(image_rect.y1)
            }
            
            # Extract caption by scanning text blocks immediately below the image
            caption = None
            blocks_below = []
            for b in blocks:
                if "lines" in b:
                    b_y0 = b["bbox"][1]
                    # Block is below the image and within 150 points
                    if b_y0 >= image_rect.y1 and b_y0 <= image_rect.y1 + 150:
                        b_text = "".join(span.get("text", "") for line in b["lines"] for span in line["spans"]).strip()
                        if b_text:
                            blocks_below.append((b_y0 - image_rect.y1, b_text))
                            
            blocks_below.sort(key=lambda x: x[0])
            
            for dist, text in blocks_below:
                # Look for lines starting with Fig or Figure
                if re.match(r'^[Ff]ig(ure)?\b', text):
                    caption = text
                    break
                    
            # Determine section figure falls under
            y_center = (image_rect.y0 + image_rect.y1) / 2
            section_title = "Introduction"
            
            # Find heading above figure closest to center
            headings_y = []
            # Recalculate median to filter headings correctly
            sizes = [span.get("size", 10.0) for b in blocks if "lines" in b 
                     for l in b["lines"] for span in l["spans"] if span.get("text", "").strip()]
            median_size = statistics.median(sizes) if sizes else 10.0
            
            for b in blocks:
                if "lines" in b:
                    b_text = "".join(s.get("text", "") for l in b["lines"] for s in l["spans"]).strip()
                    b_spans = [s for l in b["lines"] for s in l["spans"]]
                    if b_text and b_spans:
                        max_size = max(s.get("size", 0) for s in b_spans)
                        is_bold = any((s.get("flags", 0) & 2) or ("bold" in s.get("font", "").lower()) for s in b_spans)
                        if (max_size >= 1.3 * median_size) or (is_bold and len(b_text) <= 100):
                            headings_y.append((b_text, b["bbox"][1]))
                            
            headings_above = [h for h in headings_y if h[1] < y_center]
            if headings_above:
                headings_above.sort(key=lambda x: x[1], reverse=True)
                section_title = headings_above[0][0]
            elif page_sections:
                section_title = page_sections[0]["title"]
                
            extracted_figures.append(ExtractedFigure(
                page_number=page_num + 1,
                image_path=f"/data/images/{filename}",
                bbox=bbox,
                caption=caption,
                section_title=section_title
            ))
            
    doc.close()
    return extracted_figures
