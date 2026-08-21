# Hybrid Graph + Vector RAG

A hybrid Retrieval-Augmented Generation (RAG) system that combines semantic vector search with knowledge-graph retrieval to provide context-aware answers from uploaded documents.

## Tech Stack

- Frontend: React
- Backend: FastAPI
- LLM: Google Gemini
- Vector Database: Qdrant
- Graph Database: Neo4j
- Framework: LangChain
- Deployment: Docker Compose

## How It Works

1. Documents are processed using Gemini to extract relevant information.
2. Document representations are converted into embeddings and stored in Qdrant.
3. Entities and relationships are extracted and stored in Neo4j as a knowledge graph.
4. User queries are first processed using graph-based retrieval through Neo4j.
5. If graph retrieval cannot provide a useful answer, the system falls back to semantic search using Qdrant.
6. Gemini generates the final response using the retrieved context.

## Architecture

```text
React
  |
FastAPI
  |
  +---- Neo4j (Graph Retrieval)
  |
  +---- Qdrant (Vector Retrieval)
  |
Gemini (Generation)