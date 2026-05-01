import os
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_core.rate_limiters import InMemoryRateLimiter

# Load environment variables once
load_dotenv()

# --- 1. FastAPI Instance ---
# Person B (API) and Person A (Services) both reference this
app = FastAPI()

# --- 2. Throttling Configuration ---
# Shared limiter: 1 request every 10 seconds to protect Gemini Free Tier
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.1, 
    max_bucket_size=1  
)

# --- 3. Shared Constants ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "multimodal_collection_v2"

# --- 4. Database Credentials ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")