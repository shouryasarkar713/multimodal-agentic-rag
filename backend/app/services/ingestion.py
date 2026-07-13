import logging
import uuid
import traceback
from app.dependencies import async_session_factory
from app.models.db import Document
from app.services.parsing import extract_metadata, extract_pages, extract_tables, extract_figures
from app.services.chunking import chunk_text, chunk_tables, create_image_chunks
from app.services.embedding import embed_text_batch, embed_image, caption_image

async def run_ingestion_pipeline(document_id: uuid.UUID):
    """Orchestrate the 10-step document ingestion pipeline."""
    logging.info(f"Starting ingestion pipeline for document {document_id}")
    
    async with async_session_factory() as session:
        # Retrieve document
        doc = await session.get(Document, document_id)
        if not doc:
            logging.error(f"Document {document_id} not found in database.")
            return
            
        pdf_path = f"/data/uploads/{document_id}.pdf"
        
        try:
            # Step 1: PDF Metadata Extraction
            metadata = extract_metadata(pdf_path)
            doc.title = metadata["title"]
            doc.authors = metadata["authors"]
            doc.total_pages = metadata["total_pages"]
            await session.commit()
            
            # Step 2: Page-by-Page Text Extraction
            pages_content = extract_pages(pdf_path)
            
            # Step 3: Table Detection and Extraction
            extracted_tables = extract_tables(pdf_path, pages_content)
            
            # Step 4: Figure/Image Extraction
            extracted_figures = extract_figures(pdf_path, str(document_id), pages_content)
            
            # Step 5: Text Chunking
            text_chunks = chunk_text(pages_content, extracted_tables)
            
            # Step 6: Table Chunking
            table_chunks = chunk_tables(extracted_tables)
            
            # Step 7: Image Chunk Creation + Captioning
            image_chunks = create_image_chunks(extracted_figures)
            for ic in image_chunks:
                # Find surrounding text context for the figure (first 1000 chars of page full text)
                page_data = next((p for p in pages_content if p.page_number == ic.page_number), None)
                context_text = page_data.full_text[:1000] if page_data else ""
                
                # Vision captioning using GPT-4.1
                ai_caption = caption_image(ic.image_path, context_text)
                ic.image_caption = ai_caption
            
            # Combine all chunks
            all_chunks = text_chunks + table_chunks + image_chunks
            
            # Step 8: Embedding Generation
            # Batch text and table chunks for OpenAI embedding
            embed_texts = []
            text_table_indices = []
            for idx, c in enumerate(all_chunks):
                if c.content_type == "text":
                    embed_texts.append(c.content_text)
                    text_table_indices.append(idx)
                elif c.content_type == "table":
                    embed_texts.append(c.content_markdown)
                    text_table_indices.append(idx)
                    
            if embed_texts:
                embeddings = embed_text_batch(embed_texts)
                for i, emb in zip(text_table_indices, embeddings):
                    all_chunks[i].text_embedding = emb
                    
            # Compute image embeddings (CLIP Vision + OpenAI text embedding of caption)
            image_caption_texts = []
            image_indices = []
            for idx, c in enumerate(all_chunks):
                if c.content_type == "image":
                    c.image_embedding = embed_image(c.image_path)
                    image_caption_texts.append(c.image_caption or c.content_text or "")
                    image_indices.append(idx)
                    
            if image_caption_texts:
                caption_embeddings = embed_text_batch(image_caption_texts)
                for i, emb in zip(image_indices, caption_embeddings):
                    all_chunks[i].text_embedding = emb
                    
            # Associate document_id to all chunks
            for c in all_chunks:
                c.document_id = document_id
                
            # Step 9: Database Insert
            session.add_all(all_chunks)
            
            # Step 10: Status Update -> Ready
            doc.status = "ready"
            doc.error_message = None
            await session.commit()
            logging.info(f"Ingestion pipeline completed successfully for document {document_id}")
            
        except Exception as e:
            await session.rollback()
            error_str = traceback.format_exc()
            logging.error(f"Error in ingestion pipeline for document {document_id}: {error_str}")
            
            # Update status to error
            doc.status = "error"
            doc.error_message = str(e)
            await session.commit()
