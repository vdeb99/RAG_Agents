import os
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_neo4j import Neo4jGraph
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from dotenv import load_dotenv
from config import app,rate_limiter, QDRANT_URL, COLLECTION_NAME

load_dotenv()

# --- Configurations ---
# rate_limiter = InMemoryRateLimiter(requests_per_second=0.1, max_bucket_size=1)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# QDRANT_URL = "http://qdrant:6333"
# COLLECTION_NAME = "multimodal_collection_v2"

from config import app # Ensure app is imported
llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash-lite", rate_limiter=rate_limiter)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2-preview", 
    rate_limiter=rate_limiter,
    task_type="retrieval_document"
)

q_client = QdrantClient(url=QDRANT_URL)
graph = None

# Initialize Databases
for i in range(15):
    try:
        graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        collections = q_client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            q_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=rest.VectorParams(size=3072, distance=rest.Distance.COSINE)
            )
        break
    except Exception as e:
        time.sleep(5)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception))
def safe_graph_call(chain, query):
    return chain.invoke(query)

async def get_multimodal_summary(file_bytes: bytes, mime_type: str):
    message = HumanMessage(content=[
        {"type": "text", "text": "Analyze this file. Extract entities and relationships. Be concise."},
        {"type": "media", "mime_type": mime_type, "data": file_bytes}
    ])
    response = await llm.ainvoke([message])
    return response.content

def update_knowledge_graph(text: str, filename: str):
    prompt = f"Extract 15 nodes/edges as JSON: {text}"
    raw = llm.invoke(prompt).content
    clean_json = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean_json)
    
    for n in data.get('nodes', []):
        graph.query(f"MERGE (node:`{n.get('type', 'Entity')}` {{name: $id}})", {"id": n.get('id')})
    for e in data.get('edges', []):
        graph.query(f"MATCH (a {{name: $s}}), (b {{name: $t}}) MERGE (a)-[:`{e.get('rel', 'RELATED_TO')}`]->(b)", 
                    {"s": e.get('source'), "t": e.get('target')})
    graph.query("MERGE (:Document {name: $name})", {"name": filename})

async def run_vector_fallback(query_text: str):
    query_embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview", task_type="retrieval_query", rate_limiter=rate_limiter)
    vector_store = QdrantVectorStore(client=q_client, collection_name=COLLECTION_NAME, embedding=query_embeddings)
    docs = vector_store.similarity_search(query_text, k=3)
    context = "\n".join([d.page_content for d in docs])
    if not context: return {"answer": "No relevant info found."}
    res = await llm.ainvoke(f"Context: {context}\n\nQuestion: {query_text}")
    return {"answer": res.content}