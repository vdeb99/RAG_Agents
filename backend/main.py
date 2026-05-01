import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_qdrant import QdrantVectorStore
from langchain_neo4j import GraphCypherQAChain

# Import everything from the services file
# from config import app, embeddings, QDRANT_URL, COLLECTION_NAME
# from services import *
import services

# app = FastAPI() # Re-initializing or using the imported app
app=services.app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    query: str

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        summary = await services.get_multimodal_summary(content, file.content_type)
        
        await QdrantVectorStore.afrom_texts(
            texts=[summary],
            embedding=services.embeddings,
            url=services.QDRANT_URL,
            collection_name=services.COLLECTION_NAME,
            metadatas=[{"source": file.filename}]
        )
        
        services.update_knowledge_graph(summary, file.filename)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def handle_chat(payload: Query):
    try:
        chain = GraphCypherQAChain.from_llm(services.llm, graph=services.graph, verbose=True, allow_dangerous_requests=True)
        result = services.safe_graph_call(chain, payload.query)
        answer = result.get("result")

        if not answer or "I don't know" in answer:
            return await services.run_vector_fallback(payload.query)
        return {"answer": answer}

    except Exception as e:
        if "429" in str(e):
            return {"answer": "API Busy. Retrying..."}
        return await services.run_vector_fallback(payload.query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)