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

def _clean_author_name(raw: str) -> Optional[str]:
    # Strip footnote marks, digits, symbols
    s = re.sub(r'[\*†‡§#~^]', '', raw)
    s = re.sub(r'\d+', '', s)
    s = re.sub(r'\s+', ' ', s).strip(' ,;:.-')
    if not s or len(s) < 3 or len(s) > 50:
        return None
    # Filter out email-like or url-like strings
    if '@' in s or 'http' in s or 'www' in s:
        return None
    # Filter out common affiliation / header words
    lower = s.lower()
    if any(w in lower for w in [
        "university", "department", "institute", "laboratory", "school", "center",
        "faculty", "college", "corporation", "google", "meta", "microsoft", "amazon",
        "deepmind", "research", "abstract", "introduction", "arxiv", "preprint",
        "equal contribution", "toronto", "brain"
    ]):
        return None
    # Must have 2 to 5 words (First [Middle] Last)
    words = s.split()
    if 2 <= len(words) <= 5:
        # Check that words look like capitalized name parts or initials
        if all(w[0].isupper() or w.lower() in ['de', 'van', 'von', 'der', 'al', 'el', 'da', 'di'] for w in words if w):
            return s
    return None

def extract_authors_from_first_page(first_page: fitz.Page, title: str) -> Optional[List[str]]:
    """Extract author names from page 1 text blocks between title and abstract."""
    try:
        blocks = first_page.get_text("dict").get("blocks", [])
        title_lower = title.lower()

        found_title = False
        candidates = []

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_spans = line.get("spans", [])
                line_text = "".join(span.get("text", "") for span in line_spans).strip()
                if not line_text:
                    continue

                line_lower = line_text.lower()

                # If we encounter "Abstract", stop extracting authors
                if re.match(r'^(?:abstract|summary)\b', line_text, re.IGNORECASE):
                    return candidates[:12] if candidates else None

                # Check if this line is part of the title
                if not found_title:
                    title_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', title_lower).split() if len(w) > 3]
                    if any(w in line_lower for w in title_words) or (title_lower and line_lower in title_lower):
                        found_title = True
                    continue

                # Skip if line contains title text
                if line_lower in title_lower or title_lower in line_lower:
                    continue

                # Check if line looks like affiliations or emails
                is_affiliation = any(w in line_lower for w in [
                    "university", "department", "institute", "google", "research", "laborator",
                    "college", "school", "faculty", "hospital", "center", "centre", "division",
                    "@", "http", "github", "correspond", "equal contribution", "work done while"
                ])
                if is_affiliation:
                    continue

                # Author names might be separate spans or comma-separated
                for span in line_spans:
                    txt = span.get("text", "").strip()
                    if txt:
                        parts = re.split(r'[,;]|\band\b', txt)
                        for p in parts:
                            cleaned = _clean_author_name(p)
                            if cleaned and cleaned not in candidates:
                                candidates.append(cleaned)

        if candidates:
            return candidates[:12]
    except Exception as e:
        logging.warning(f"Failed to extract authors from first page: {e}")
    return None

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
            
    # Fallback author extraction from page 1 if PDF metadata is missing
    if not authors and len(doc) > 0:
        authors = extract_authors_from_first_page(doc[0], title)

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
    """Extract figures (both vector diagrams and raster images) from PDF with their captions.
    
    In academic papers, figures are frequently vector graphics (paths/strokes)
    placed directly above (or occasionally below) a caption starting with 'Fig.' or 'Figure'.
    This function detects figure captions, computes the bounding box of the visual figure
    (from vector paths, text labels, and raster images), renders the cropped region at 200 DPI,
    and extracts standalone raster images while filtering out logos/decorations.
    """
    logging.info(f"Extracting figures from {pdf_path}")
    extracted_figures = []
    
    os.makedirs("/data/images", exist_ok=True)
    doc = fitz.open(pdf_path)
    
    fig_caption_re = re.compile(r'^\s*(?:Fig(?:ure)?\.?)\s*(\d+)', re.IGNORECASE)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_sections = []
        if page_num < len(pages_content):
            page_sections = pages_content[page_num].sections
            
        page_dict = page.get_text("dict")
        blocks = page_dict.get("blocks", [])
        
        # 1. Identify headings on this page for section attribution
        headings_y = []
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
                        
        def get_section_title(y_coord: float) -> str:
            headings_above = [h for h in headings_y if h[1] < y_coord]
            if headings_above:
                headings_above.sort(key=lambda x: x[1], reverse=True)
                return headings_above[0][0]
            elif page_sections:
                return page_sections[0]["title"]
            return "Introduction"
            
        # 2. Find all figure captions on this page
        caption_items = []
        for b_idx, b in enumerate(blocks):
            if "lines" not in b:
                continue
            block_text = "".join(s.get("text", "") for l in b["lines"] for s in l["spans"]).strip()
            normalized_text = re.sub(r'\s+', ' ', block_text)
            match = fig_caption_re.match(normalized_text)
            if match:
                fig_num = int(match.group(1))
                cap_rect = fitz.Rect(b["bbox"])
                caption_items.append({
                    "fig_num": fig_num,
                    "caption": normalized_text,
                    "rect": cap_rect,
                    "block_idx": b_idx
                })
            else:
                # Also check if caption starts slightly inside block
                search_match = re.search(r'(?:^|\n)\s*(Fig(?:ure)?\.?\s*\d+[^.\n]*\..*)', block_text, re.IGNORECASE | re.DOTALL)
                if search_match:
                    cap_candidate = re.sub(r'\s+', ' ', search_match.group(1)).strip()
                    num_m = re.search(r'\d+', cap_candidate)
                    if num_m:
                        cap_rect = fitz.Rect(b["bbox"])
                        caption_items.append({
                            "fig_num": int(num_m.group(0)),
                            "caption": cap_candidate,
                            "rect": cap_rect,
                            "block_idx": b_idx
                        })
                
        # Sort captions vertically (top to bottom)
        caption_items.sort(key=lambda c: c["rect"].y0)
        
        # Track regions already covered by extracted figures to avoid duplicate raster extractions
        extracted_clip_rects = []
        
        # 3. For each caption, locate and extract the figure
        all_drawings = page.get_drawings()
        
        prev_cap_bottom = 0.0
        for c_idx, cap in enumerate(caption_items):
            cap_rect = cap["rect"]
            
            # Determine top boundary for this figure:
            # Look at body text blocks strictly above this caption and below previous caption
            body_blocks_above = []
            for b_idx, b in enumerate(blocks):
                if "lines" not in b:
                    continue
                # Don't consider captions
                if any(c["block_idx"] == b_idx for c in caption_items):
                    continue
                b_rect = fitz.Rect(b["bbox"])
                b_text = "".join(s.get("text", "") for l in b["lines"] for s in l["spans"]).strip()
                # A body block must end above the caption, but below prev_cap_bottom
                if b_rect.y1 <= cap_rect.y0 - 6 and b_rect.y1 >= prev_cap_bottom:
                    # Filter out short isolated diagram labels (which belong to the figure, not body text)
                    if len(b_text) > 40 or b_rect.width > 180:
                        body_blocks_above.append(b_rect)
                        
            if body_blocks_above:
                y_top = max(b.y1 for b in body_blocks_above) + 2.0
            else:
                # Top of page content (below running header ~50pt)
                y_top = max(prev_cap_bottom, 50.0)
                
            y_bottom = cap_rect.y0 - 2.0
            
            # Check if there is enough vertical space above caption; if not, check below
            candidate_rects = []
            if y_bottom - y_top >= 30:
                # Search zone above caption
                for d in all_drawings:
                    dr = fitz.Rect(d["rect"])
                    if dr.is_empty or dr.is_infinite:
                        continue
                    # Skip full-page background/box rects
                    if dr.width >= page.rect.width * 0.92 and dr.height >= page.rect.height * 0.92:
                        continue
                    # Skip running header/footer lines
                    if dr.y1 < 45 or dr.y0 > page.rect.height - 40:
                        continue
                    # Check vertical overlap
                    if dr.y1 >= y_top - 4 and dr.y0 <= y_bottom + 4:
                        if dr.y0 < y_top - 20 or dr.y1 > y_bottom + 20:
                            continue
                        candidate_rects.append(dr)
                        
                # Check for raster image rects in this zone
                for img_info in page.get_images():
                    xref = img_info[0]
                    for img_r in page.get_image_rects(xref):
                        if img_r.y1 >= y_top - 4 and img_r.y0 <= y_bottom + 4:
                            candidate_rects.append(img_r)
                            
                # Check for text labels inside diagram
                for b in blocks:
                    if "lines" not in b:
                        continue
                    b_rect = fitz.Rect(b["bbox"])
                    if b_rect.y0 >= y_top - 2 and b_rect.y1 <= y_bottom + 2:
                        if not (b_rect.y0 >= cap_rect.y0 - 2 and b_rect.y1 <= cap_rect.y1 + 2):
                            candidate_rects.append(b_rect)
                            
                # Determine figure bounding box
                if candidate_rects:
                    union_rect = fitz.Rect(candidate_rects[0])
                    for r in candidate_rects[1:]:
                        union_rect.include_rect(r)
                    fig_clip = fitz.Rect(
                        max(10.0, union_rect.x0 - 8.0),
                        max(y_top, union_rect.y0 - 8.0),
                        min(page.rect.width - 10.0, union_rect.x1 + 8.0),
                        min(y_bottom, union_rect.y1 + 4.0)
                    )
                else:
                    fig_clip = fitz.Rect(
                        max(40.0, cap_rect.x0 - 15.0),
                        max(y_top, 50.0),
                        min(page.rect.width - 40.0, max(cap_rect.x1 + 15.0, page.rect.width - 50.0)),
                        y_bottom
                    )
            else:
                # Figure might be below caption
                y_top_below = cap_rect.y1 + 2.0
                next_blocks = [fitz.Rect(b["bbox"]) for b in blocks if "lines" in b and fitz.Rect(b["bbox"]).y0 >= y_top_below + 10]
                y_bottom_below = min([b.y0 for b in next_blocks] + [page.rect.height - 40.0])
                for d in all_drawings:
                    dr = fitz.Rect(d["rect"])
                    if not dr.is_empty and dr.y1 >= y_top_below and dr.y0 <= y_bottom_below:
                        candidate_rects.append(dr)
                if candidate_rects:
                    union_rect = fitz.Rect(candidate_rects[0])
                    for r in candidate_rects[1:]:
                        union_rect.include_rect(r)
                    fig_clip = fitz.Rect(
                        max(10.0, union_rect.x0 - 8.0),
                        max(y_top_below, union_rect.y0 - 8.0),
                        min(page.rect.width - 10.0, union_rect.x1 + 8.0),
                        min(y_bottom_below, union_rect.y1 + 4.0)
                    )
                else:
                    fig_clip = fitz.Rect(
                        max(40.0, cap_rect.x0 - 15.0),
                        y_top_below,
                        min(page.rect.width - 40.0, max(cap_rect.x1 + 15.0, page.rect.width - 50.0)),
                        y_bottom_below
                    )
                
            # Sanity check figure dimensions
            if fig_clip.width >= 40 and fig_clip.height >= 30:
                filename = f"{document_id}_fig_{page_num + 1}_{cap['fig_num']}.png"
                image_path = f"/data/images/{filename}"
                
                try:
                    pix = page.get_pixmap(clip=fig_clip, dpi=200)
                    pix.save(image_path)
                    
                    bbox = {
                        "x0": float(fig_clip.x0),
                        "y0": float(fig_clip.y0),
                        "x1": float(fig_clip.x1),
                        "y1": float(fig_clip.y1)
                    }
                    
                    section_title = get_section_title((fig_clip.y0 + fig_clip.y1) / 2)
                    
                    extracted_figures.append(ExtractedFigure(
                        page_number=page_num + 1,
                        image_path=f"/data/images/{filename}",
                        bbox=bbox,
                        caption=cap["caption"],
                        section_title=section_title
                    ))
                    extracted_clip_rects.append(fig_clip)
                    logging.info(f"Extracted Fig {cap['fig_num']} on page {page_num + 1}: {fig_clip}")
                except Exception as e:
                    logging.warning(f"Failed to render figure {cap['fig_num']} on page {page_num + 1}: {e}")
                    
            prev_cap_bottom = cap_rect.y1
            
        # 4. Standalone raster images (for figures that don't have standard 'Fig.' captions)
        for img_idx, img_info in enumerate(page.get_images(full=True)):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            if not base_image:
                continue
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            
            # Skip small icons/logos
            if width < 100 or height < 100:
                continue
                
            rects = page.get_image_rects(xref)
            image_rect = rects[0] if rects else None
            if not image_rect:
                continue
                
            # Filter publisher header logos (page 1 top 20%)
            if page_num == 0 and image_rect.y0 < 180:
                continue
                
            # Skip if already captured in a figure clip
            already_captured = False
            for c_rect in extracted_clip_rects:
                if (image_rect.x0 >= c_rect.x0 - 10 and image_rect.x1 <= c_rect.x1 + 10 and
                    image_rect.y0 >= c_rect.y0 - 10 and image_rect.y1 <= c_rect.y1 + 10):
                    already_captured = True
                    break
            if already_captured:
                continue
                
            # Save standalone image
            filename = f"{document_id}_raw_{page_num + 1}_{img_idx}.png"
            image_path = f"/data/images/{filename}"
            with open(image_path, "wb") as f_out:
                f_out.write(base_image["image"])
                
            bbox = {
                "x0": float(image_rect.x0),
                "y0": float(image_rect.y0),
                "x1": float(image_rect.x1),
                "y1": float(image_rect.y1)
            }
            
            section_title = get_section_title((image_rect.y0 + image_rect.y1) / 2)
            
            extracted_figures.append(ExtractedFigure(
                page_number=page_num + 1,
                image_path=f"/data/images/{filename}",
                bbox=bbox,
                caption=f"Image from page {page_num + 1}",
                section_title=section_title
            ))
            
    doc.close()
    logging.info(f"Total extracted figures: {len(extracted_figures)}")
    return extracted_figures
