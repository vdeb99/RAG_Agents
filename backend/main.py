import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_qdrant import QdrantVectorStore
from langchain_neo4j import GraphCypherQAChain

# Import everything from the services file
from services import (
    app, llm, graph, embeddings, QDRANT_URL, COLLECTION_NAME, 
    get_multimodal_summary, update_knowledge_graph, run_vector_fallback, safe_graph_call
)

app = FastAPI() # Re-initializing or using the imported app

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
        summary = await get_multimodal_summary(content, file.content_type)
        
        await QdrantVectorStore.afrom_texts(
            texts=[summary],
            embedding=embeddings,
            url=QDRANT_URL,
            collection_name=COLLECTION_NAME,
            metadatas=[{"source": file.filename}]
        )
        
        update_knowledge_graph(summary, file.filename)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def handle_chat(payload: Query):
    try:
        chain = GraphCypherQAChain.from_llm(llm, graph=graph, verbose=True, allow_dangerous_requests=True)
        result = safe_graph_call(chain, payload.query)
        answer = result.get("result")

        if not answer or "I don't know" in answer:
            return await run_vector_fallback(payload.query)
        return {"answer": answer}

    except Exception as e:
        if "429" in str(e):
            return {"answer": "API Busy. Retrying..."}
        return await run_vector_fallback(payload.query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)