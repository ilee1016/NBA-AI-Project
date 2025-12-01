# NBA AI Project — End-to-End RAG + Chat Interface

This project is an end-to-end Retrieval-Augmented Generation (RAG) system for answering NBA game and player statistics questions using structured data, semantic search, and a lightweight LLM. It includes a fully working backend pipeline as well as an interactive Angular-based frontend chat interface.

## Project Overview

The system has three major components:

### **1. Data Pipeline (Ingestion + Embeddings)**
Located in `backend/ingest.py` and `backend/embed.py`

- Loads NBA game data (2023–24 and 2024–25 seasons) into PostgreSQL tables  
- Generates text embeddings using **nomic-embed-text** through an Ollama container  
- Stores embeddings with game summaries using the PostgreSQL `pgvector` extension  

**Purpose:**  
Provide a semantic search layer on top of structured NBA stats.

---

### **2. Retrieval + Answering (RAG Pipeline)**
Located in `backend/rag.py`

- Performs semantic retrieval using embedding similarity  
- Joins retrieved embeddings back to the original box-score data  
- Uses **llama3.2:3b** to generate grounded answers  
- Outputs responses and evidence for each query  

**Purpose:**  
Enable accurate, data-grounded question-answering across NBA stats.

---

### **3. Frontend Chat Interface**
Located in `frontend/`

- Built with Angular  
- Provides a clean chat interface for user queries  
- Sends requests to a FastAPI backend (`backend/server.py`)  
- Displays responses, evidence, and context retrieved from the RAG system  

**Purpose:**  
Let users ask natural-language questions and get interactive, real-time results.

---

## 🧪 Running the Project

### **Backend**
```bash
docker compose up -d db ollama
docker exec ollama ollama pull nomic-embed-text
docker exec ollama ollama pull llama3.2:3b
docker compose build app
