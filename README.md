# Multimodal Technical Research Assistant with Agentic RAG

A state-of-the-art engineering-locked RAG platform for analyzing complex technical research papers. Leveraging LangGraph, FastAPI, pgvector, and Next.js, this assistant processes text, extracts and parses figures, decomposes multi-paper comparative queries, and provides verifiable, citation-backed answers with visual context and complete execution tracing.

**Live Demo**: [http://research-gpt.duckdns.org/](http://research-gpt.duckdns.org/)

---

## 🚀 Key Features

*   **Multimodal Ingestion**: Page-by-page text parsing (PyMuPDF) and table extraction (pdfplumber) into Markdown tables.
*   **Visual Analysis & Fuzzy Figure Explanations**: Extracts figure image files and generates visual summaries using GPT-4o vision models, embedded with CLIP. Incorporates robust regex-based fuzzy figure matching (e.g., `Figure 3`, `Fig 3`) and direct visual context queries (`EXPLAIN_FIGURE: <uuid>`) mapped with GPT-4o vision analysis.
*   **Stateful Agentic Routing**: Analyzes intent and routes queries to specific sub-graphs (`paper_qa`, `compare`, `summarize`, `action`).
*   **Multi-Hop Query Decomposition**: Compares datasets, training regimes, and results across multiple papers side-by-side.
*   **Hallucination Guardrails**: Employs double-loop validation to grade retrieved evidence and cross-examine generated claims before rendering.
*   **Observability Timeline**: Custom dashboard tracing node runtimes, input/output structures, and raw execution metadata.
*   **Markdown Export**: One-click download of citation-backed responses and referencing figures.

---

## 🛠️ Tech Stack & Requirements

*   **Frontend**: Next.js 14 (App Router), React, Tailwind CSS 3.4, TypeScript, Lucide Icons, remark-gfm.
*   **Backend**: FastAPI 0.115, Python 3.12, SQLAlchemy 2.0, Alembic (Migrations).
*   **Vector Database**: PostgreSQL 16 with pgvector 0.7.
*   **Models**: OpenAI `gpt-4o` (LLM/Vision), `text-embedding-3-small` (Text Embeddings), `ViT-B-32` (CLIP Vision Embeddings via open_clip).

---

## ⚙️ Environment Variables

Copy the template `.env.example` to `.env` in the root workspace directory:

```bash
cp .env.example .env
```

Define the following environment variables:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | OpenAI API credential. Used for chat generation, vision captioning, and embeddings. | `sk-proj-...` |
| `DATABASE_URL` | Async connection string for PostgreSQL database. | `postgresql+asyncpc://postgres:postgres@db:5432/research_assistant` |
| `API_KEY` | Secret token used to authorize requests between frontend and backend via the `X-API-Key` header. | `test-api-key-123` |
| `LANGSMITH_API_KEY` | (Optional) API key for LangSmith execution tracing. | `lsv2_pt_...` |
| `LANGSMITH_PROJECT` | (Optional) Project name in LangSmith console. | `multimodal-agentic-rag` |
| `DATA_DIR` | Absolute path for local-first uploads and extracted images. | `/data` |

---

## 📦 Getting Started & Run Instructions

### Local Run Instructions
Follow these steps to spin up the system from a clean clone locally:

#### 1. Start the Containers
Ensure Docker and Docker Compose are installed, then build and run the services:
```bash
docker compose up -d --build
```
This launches three main services:
*   `db`: PostgreSQL database on port `5432`
*   `backend`: FastAPI server on `http://localhost:8000` (Swagger UI at `http://localhost:8000/docs`)
*   `frontend`: Next.js application on `http://localhost:3000` (by default)

#### 2. Run Database Migrations
Once the database container is healthy, run the Alembic migrations to set up the schema:
```bash
docker compose exec backend alembic upgrade head
```

---

### Cloud Deployment (AWS EC2 & Supabase)
To host the application persistently in the cloud:

#### 1. Set up a Static IP (Elastic IP)
*   Allocate an **Elastic IP** in your AWS console and associate it with your running EC2 instance. This prevents the server IP from changing on reboots.

#### 2. Configure Ports & API URLs
*   In `docker-compose.yml`, update the `NEXT_PUBLIC_API_URL` environment variable for the frontend:
    ```yaml
    - NEXT_PUBLIC_API_URL=http://<YOUR_STATIC_IP>:8000/api
    ```
*   Map the frontend port to `80` (standard HTTP port) to access the app without typing a port number:
    ```yaml
    ports:
      - "80:3000"
    ```

#### 3. Update AWS Firewall (Security Group)
*   Open inbound TCP ports **80** (HTTP) and **8000** (Backend API) to anywhere (`0.0.0.0/0`) in your EC2 Security Group.

#### 4. Configure a Custom Domain (Optional & Free)
*   Register a free subdomain (e.g. `your-app.duckdns.org`) on [DuckDNS](https://www.duckdns.org) and set the target IP to your AWS Elastic IP.

#### 5. Launch & Apply Migrations
*   Build and launch the containers on the VM:
    ```bash
    git pull
    docker compose up -d --build
    ```
*   Migrate the Supabase database:
    ```bash
    docker compose exec backend alembic upgrade head
    ```

---

## 📖 Usage Walkthrough

### 1. Ingest Papers
*   Open the Dashboard landing page at `http://localhost:3000`.
*   Use the drag-and-drop zone to upload PDF research papers (up to 100 pages, max 50 MB).
*   The page will show a progress bar. The document list will show a yellow `processing` status while PyMuPDF/pdfplumber parse text, extract tables, crop figures, and generate embeddings. When finished, it turns green (`ready`).

### 2. Scope & Chat
*   Navigate to the **Chat** panel.
*   Type a research question (e.g., *"What is the main goal of residual learning?"*).
*   Use the **Scope to documents** dropdown to select the target paper(s).
*   Submit the query. The response will include:
    *   An answer with superscript citations (e.g. `[1]`). Clicking these scrolls to the detailed excerpt cards at the bottom.
    *   A color-coded **Confidence Badge** (Green for high, Yellow for medium, Red for low).
    *   A link to **View Trace Timeline** for execution visibility.
    *   Figure thumbnail attachments. Clicking a thumbnail opens a high-resolution lightbox with a **"Explain this figure"** action.

### 3. Compare Papers
*   Navigate to the **Compare** panel.
*   Select two papers (Paper A and Paper B).
*   Submit a query (e.g., *"Compare the optimizer choices and learning rates"*).
*   Results will populate in side-by-side columns with a synthesis summary below them.

### 4. Export Markdown
*   Click the **Export** button on any assistant message bubble to download the response, citations, and figure paths compiled as a structured `.md` file.

---

## 📊 Running the Evaluation Suite

We include an automated evaluation script that tests the RAG pipeline against a gold-standard dataset of **30 Q&A pairs** grounded in three prominent ML papers:
1.  **Attention Is All You Need** (`1706.03762`)
2.  **ResNet** (`1512.03385`)
3.  **BERT** (`1810.04805`)

### 1. Download and Ingest the Evaluation Papers
Ensure the containers are running, then navigate to `http://localhost:3000/download_helper.html` in your browser. Click **Start Download** to trigger background fetching and ingestion of the three papers directly from arXiv.

Alternatively, execute a POST call using the backend Swagger UI at `/api/documents/download_arxiv` with the paper IDs.

Wait until all three papers show `ready` in the document library.

### 2. Run the Evaluation Runner
Execute the evaluation suite inside the backend container:
```bash
docker compose exec backend python eval/eval_runner.py
```
This runs the 30 queries, grades the outputs using `gpt-4o-mini`, and prints a report table.

### 3. Targets and Metrics
The evaluation verifies four core metrics against target thresholds:
*   **Faithfulness** ($\ge 0.85$): Ensures answer claims are strictly grounded in retrieved text chunks.
*   **Answer Relevancy** ($\ge 0.80$): Computes semantic embedding similarity of generated queries.
*   **Context Precision** ($\ge 0.70$): Assesses if relevant chunks are ranked at the top of results.
*   **Citation Accuracy** ($\ge 0.90$): Checks that inline citations point to chunks containing the cited information.
