<div align="center">

# ⚡ InsightForge AI

### Autonomous Multi-Agent Research, Document Intelligence & Grounded Decision Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google%20gemini&logoColor=white)](https://ai.google.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F61?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![Supabase](https://img.shields.io/badge/Supabase%20PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<p align="center">
  <strong>Transform raw documents, spreadsheets, slides, and websites into publication-grade research, audit-ready comparative matrices, and executive briefings with zero hallucinations.</strong>
</p>

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Multi-Agent Pipeline](#-multi-agent-orchestration-dag) •
[Quickstart](#-quickstart--local-setup) •
[API Reference](#-api-endpoints) •
[Tech Stack](#-tech-stack)

</div>

---

## 🌟 Key Features

### 1. Dual-Stage Neural RAG with Cross-Encoder Reranking
* **Dense Semantic Indexing:** High-dimensional vector indexing using `sentence-transformers/all-MiniLM-L6-v2` via persistent ChromaDB.
* **Hybrid Search (BM25 + Dense RRF):** Combines keyword exact-match frequency (BM25) with semantic vector similarity via Reciprocal Rank Fusion ($\alpha$-weighted).
* **Neural Cross-Encoder Reranker:** Eliminates false positives by evaluating candidate chunks using `cross-encoder/ms-marco-MiniLM-L-6-v2` with deep query-document cross-attention.
* **Strict Hallucination Guard:** Answers are strictly grounded in retrieved evidence. If evidence is absent, the system explicitly indicates missing context rather than fabricating information.

### 2. Autonomous Multi-Agent Research DAG
Deploys a specialized team of 6 autonomous agents for comprehensive research:
* 🧭 **Planner Agent:** Dissects ambiguous queries into structured research subtasks.
* 🔍 **Research Agent:** Performs multi-hop retrieval and contextual chunk aggregation.
* 📊 **Analyst Agent:** Synthesizes thematic patterns across heterogeneous documents.
* ⚖️ **Critic Agent:** Conducts adversarial scrutiny to detect logical leaps and unverified assumptions.
* 🛡️ **Fact-Checker Agent:** Validates every claim against source excerpts and computes an empirical **Grounding Score (%)**.
* 📝 **Synthesizer Agent:** Generates executive-ready research reports with methodology, citations, and strategic recommendations.

### 3. Multimodal & Handwritten Document Intelligence
* **Multi-Format Ingestion:** Native extraction for `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.txt`, `.md`, and **Live Web URLs**.
* **Handwriting & Scanned Document OCR:** Automatically detects non-digital or scanned PDFs and routes them to the **Google Gemini Multimodal Vision Engine** to accurately transcribe cursive writing, handwritten notes, student assignments, and mathematical notations.

### 4. Interactive Document Comparison & Conflict Matrix
* Upload two versions of a contract, syllabus, or financial report to generate an automated **Semantic Diff Matrix**.
* Identifies newly introduced clauses, deleted sections, governance shifts, and operational risk ratings.

### 5. Multi-Tenant Cloud Architecture & Ephemeral Guest Sessions
* **Supabase Cloud PostgreSQL:** High-performance session pooling and persistent storage for user accounts, cloud documents, and chat history.
* **Row Level Security (RLS):** Strict multi-tenant data isolation; users cannot access documents or threads belonging to others.
* **Ephemeral Guest Mode:** Unauthenticated visitors can freely test and explore; temporary sessions and chats are automatically purged upon tab close or logout.

### 6. Executive Audio Podcast Briefing Generator
* Converts extensive research reports into engaging, professional 2-minute executive podcast briefing scripts for on-the-go consumption.

---

## 🏗 System Architecture

```mermaid
flowchart TD
    User([User / Browser]) <--> Frontend[React 18 + Vite + Tailwind CSS]
    
    Frontend <-->|REST API + JWT Bearer| Backend[FastAPI Async Backend]
    
    subgraph Storage & Cloud
        Backend <--> DB[(Supabase Cloud PostgreSQL)]
        Backend <--> VectorStore[(Persistent ChromaDB)]
        Backend <--> DiskStore[(Document Store)]
    end
    
    subgraph Two-Stage Retrieval Pipeline
        Backend --> Ingest[Universal Extractor: PyPDF + Gemini Vision]
        Ingest --> Chunker[Sentence-Boundary Chunker]
        Chunker --> Embedder[all-MiniLM-L6-v2]
        Embedder --> VectorStore
        VectorStore --> CandidateSearch[BM25 + Dense Hybrid RRF]
        CandidateSearch --> Reranker[Neural Cross-Encoder: ms-marco-MiniLM-L-6-v2]
    end
    
    subgraph Multi-Agent Orchestrator
        Reranker --> Planner[1. Planner Agent]
        Planner --> Researcher[2. Research Agent]
        Researcher --> Analyst[3. Analyst Agent]
        Analyst --> Critic[4. Critic Agent]
        Critic --> FactChecker[5. Fact-Checker Agent]
        FactChecker --> Synthesizer[6. Synthesizer Agent]
    end
    
    Synthesizer --> GeminiLLM[Google Gemini 1.5 Flash]
    GeminiLLM --> FinalReport[Grounded Report + Inline Citations + Grounding Score]
    FinalReport --> Frontend
```

---

## 📂 Project Structure

```
InsightForge-AI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI initialization & CORS middleware
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings & environment config
│   │   │   ├── gemini.py            # Gemini Client & Multimodal Vision OCR
│   │   │   ├── security.py          # Input sanitization, password hashing, JWT
│   │   │   └── logger.py            # Color-coded runtime logger
│   │   ├── db/
│   │   │   ├── session.py           # Supabase connection & automatic RLS enforcement
│   │   │   └── models.py            # SQLAlchemy models (User, Sessions, Documents, Chat)
│   │   ├── rag/
│   │   │   ├── extractor.py         # Multi-format parser (PDF, DOCX, XLSX, Web, Vision OCR)
│   │   │   ├── chunker.py           # Paragraph & sentence-aware sliding window chunker
│   │   │   ├── vector_store.py      # Persistent ChromaDB client
│   │   │   ├── reranker.py          # CrossEncoder re-scoring transformer
│   │   │   ├── hybrid_search.py     # BM25 lexical + Dense semantic RRF fusion
│   │   │   └── pipeline.py          # Grounded RAG orchestrator
│   │   ├── agents/
│   │   │   ├── planner.py           # Query decomposition agent
│   │   │   ├── research.py          # Deep evidence retrieval agent
│   │   │   ├── analyst.py           # Thematic analysis agent
│   │   │   ├── critic.py            # Adversarial review & bias detection
│   │   │   ├── fact_checker.py      # Citation verification & grounding score
│   │   │   ├── synthesizer.py       # Final report generation agent
│   │   │   └── orchestrator.py      # Multi-agent controller
│   │   ├── api/                     # REST routes (/auth, /documents, /chat, /projects, /research)
│   │   └── services/                # Business logic services
│   ├── tests/                       # Pytest automated test suites
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/              # DocumentViewerModal, ComparisonModal, Header, Sidebar
│   │   ├── context/                 # AuthContext (Google OAuth & local session state)
│   │   ├── pages/                   # Workspace, Documents, Projects, Reports, Evaluation
│   │   ├── services/                # API client with automatic Bearer token injection
│   │   ├── types/                   # TypeScript interfaces
│   │   └── App.tsx                  # Root application router & theme provider
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── documents/                       # Document storage directory
├── docker-compose.yml               # Multi-container orchestration
├── .env.example                     # Environment template
├── LICENSE                          # MIT License
└── README.md
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
* **Python 3.11+**
* **Node.js 18+ & npm**
* **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))
* *(Optional)* **Supabase Account** for Cloud PostgreSQL ([Supabase](https://supabase.com))

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/<your-username>/InsightForge-AI.git
cd InsightForge-AI
```

### Step 2: Environment Configuration
Copy the template configuration file:
```bash
cp .env.example .env
```
Open `.env` and fill in your credentials:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Supabase or local PostgreSQL URL (falls back to local SQLite automatically if omitted)
DATABASE_URL=postgresql://postgres.yourproject:yourpassword@aws-0-pooler.supabase.com:5432/postgres?sslmode=require

# Google OAuth 2.0 (Optional)
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Session Key
SESSION_SECRET=your_random_secret_key_here
```

---

### Step 3: Run Backend (FastAPI)
```bash
# Create and activate Python virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# Mac / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the API server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **Interactive OpenAPI Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Backend Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### Step 4: Run Frontend (React + Vite)
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
* **Web Application UI:** [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 🐳 Docker Deployment

Run the complete full-stack platform with a single command:
```bash
docker-compose up --build
```
* **Frontend:** [http://localhost:3000](http://localhost:3000)
* **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/google` | Authenticate / register user via Google OAuth credential |
| `POST` | `/api/auth/send-otp` | Deliver 6-digit verification code to real email inbox |
| `POST` | `/api/auth/verify-otp` | Verify OTP code and complete account registration |
| `POST` | `/api/documents/upload` | Upload & index document (PDF, Word, Excel, PPTX, CSV) |
| `POST` | `/api/documents/url` | Scrape and vectorize live webpage URL |
| `GET` | `/api/documents` | List accessible documents (filtered by user session) |
| `DELETE` | `/api/documents/{id}` | Directly delete document and purge vector embeddings |
| `POST` | `/api/documents/compare` | Run deep comparative AI analysis between two documents |
| `POST` | `/api/chat` | Ask grounded question with citation tracking |
| `GET` | `/api/chat/history` | Retrieve persistent multi-turn chat history |
| `POST` | `/api/research` | Trigger 6-agent autonomous deep research DAG |
| `POST` | `/api/research/podcast-briefing` | Generate 2-minute executive audio briefing script |

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Lucide Icons, Recharts, Vite |
| **Backend API** | FastAPI (Python 3.11+), Pydantic v2, Uvicorn, SQLAlchemy |
| **Large Language Models** | Google Gemini 1.5 Flash / 1.5 Pro |
| **Multimodal Vision OCR** | Google Gemini Multimodal Vision API |
| **Vector Database** | ChromaDB (Persistent Disk Index) |
| **Embeddings & Reranker** | `sentence-transformers/all-MiniLM-L6-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Cloud Database** | Supabase Cloud PostgreSQL with Row Level Security (RLS) & Session Pooler |
| **Containerization** | Docker, Docker Compose, Nginx |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - feel free to use it for personal, academic, or commercial applications.
