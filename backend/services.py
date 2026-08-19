import os
import json
import time
import io
import re
from typing import List

from dotenv import load_dotenv

load_dotenv()

from docx import Document as DocxDocument
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from langchain_core.messages import HumanMessage
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from langchain_qdrant import QdrantVectorStore
from langchain_neo4j import Neo4jGraph

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from config import app, rate_limiter, QDRANT_URL, COLLECTION_NAME

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")

NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash-lite",
    rate_limiter=rate_limiter,
)


embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2-preview",
    rate_limiter=rate_limiter,
    task_type="retrieval_document",
)


q_client = QdrantClient(url=QDRANT_URL)


graph = None


for i in range(15):

    try:

        print(f"Attempting database initialization " f"{i + 1}/15...")

        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
        )

        print("Neo4j connected successfully.")

        collections = q_client.get_collections().collections

        collection_exists = any(c.name == COLLECTION_NAME for c in collections)

        if not collection_exists:

            print(f"Creating Qdrant collection: " f"{COLLECTION_NAME}")

            q_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=rest.VectorParams(
                    size=3072,
                    distance=rest.Distance.COSINE,
                ),
            )

            print("Qdrant collection created.")

        else:

            print(f"Qdrant collection already exists: " f"{COLLECTION_NAME}")

        break

    except Exception as e:

        print(f"Database initialization failed: {e}")

        if i < 14:

            print("Retrying in 5 seconds...")

            time.sleep(5)

        else:

            print("Could not initialize databases " "after 15 attempts.")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(Exception),
)
def safe_graph_call(chain, query):

    return chain.invoke(query)


async def get_multimodal_summary(file_bytes: bytes, mime_type: str):

    if "officedocument.wordprocessingml.document" in mime_type:

        doc = DocxDocument(io.BytesIO(file_bytes))

        full_text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())

        prompt = f"""
Analyze the following document text.

Extract the most important entities and
relationships that would be useful for building
a knowledge graph.

Be concise.

Document:

{full_text}
"""

        response = await llm.ainvoke(prompt)

        return response.content

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Analyze this file. "
                    "If it is audio, listen carefully. "
                    "Extract the most important entities "
                    "and relationships for a knowledge graph. "
                    "Be concise."
                ),
            },
            {
                "type": "media",
                "mime_type": mime_type,
                "data": file_bytes,
            },
        ]
    )

    response = await llm.ainvoke([message])

    return response.content


def clean_json_response(raw_response: str):

    if not raw_response:
        raise ValueError("Gemini returned an empty response.")

    raw_response = str(raw_response).strip()

    raw_response = re.sub(
        r"```json\s*",
        "",
        raw_response,
        flags=re.IGNORECASE,
    )

    raw_response = re.sub(
        r"```\s*",
        "",
        raw_response,
    )

    raw_response = raw_response.strip()
    start = raw_response.find("{")
    end = raw_response.rfind("}")

    if start != -1 and end != -1:

        raw_response = raw_response[start : end + 1]

    return raw_response


def update_knowledge_graph(text: str, filename: str):

    if graph is None:

        raise RuntimeError("Neo4j graph is not initialized.")
    prompt = f"""
You are an information extraction system.

Extract entities and relationships from the text below
for a Neo4j knowledge graph.

Return ONLY valid JSON.

Do NOT return markdown.
Do NOT use ```json.
Do NOT include explanations.
Do NOT include any text before or after the JSON.

The JSON MUST follow EXACTLY this structure:

{{
    "nodes": [
        {{
            "id": "entity name",
            "type": "entity type"
        }}
    ],
    "edges": [
        {{
            "source": "source entity name",
            "target": "target entity name",
            "rel": "RELATIONSHIP"
        }}
    ]
}}

Rules:

1. Extract at most 15 nodes.
2. Extract at most 15 relationships.
3. Every edge source must correspond to a node id.
4. Every edge target must correspond to a node id.
5. Use short entity names.
6. Use simple entity types such as:
   Person, Organization, Company, Technology,
   Location, Product, Concept, Event, Document.
7. Relationship names should be uppercase with underscores.
8. Return an empty array if there are no entities.
9. Return an empty array if there are no relationships.

Text:

{text}
"""

    print(f"Extracting knowledge graph for: " f"{filename}")

    response = llm.invoke(prompt)

    raw = response.content

    print("\n================ GEMINI RAW RESPONSE ================")
    print(raw)
    print("======================================================\n")

    clean_json = clean_json_response(raw)

    print("Cleaned JSON:")

    print(clean_json)

    try:

        data = json.loads(clean_json)

    except json.JSONDecodeError as e:

        print("JSON parsing failed.")

        print(f"Gemini response: {raw}")

        raise ValueError(f"Gemini returned invalid JSON: {e}")

    if not isinstance(data, dict):

        raise ValueError(
            "Expected Gemini to return a JSON object "
            "with 'nodes' and 'edges', but received "
            f"{type(data).__name__}: {data}"
        )

    nodes = data.get("nodes", [])

    edges = data.get("edges", [])

    if not isinstance(nodes, list):

        raise ValueError("'nodes' must be a list.")

    if not isinstance(edges, list):

        raise ValueError("'edges' must be a list.")

    print(f"Extracted {len(nodes)} nodes " f"and {len(edges)} edges.")

    valid_node_ids = set()

    for node in nodes:

        if not isinstance(node, dict):
            continue

        node_id = node.get("id")

        node_type = node.get("type", "Entity")

        if not node_id:
            continue

        node_type = re.sub(r"[^a-zA-Z0-9_]", "_", str(node_type))

        if not node_type:
            node_type = "Entity"

        valid_node_ids.add(str(node_id))

        try:

            graph.query(
                f"""
                MERGE (
                    node:`{node_type}`
                    {{name: $id}}
                )
                """,
                {"id": str(node_id)},
            )

        except Exception as e:

            print(f"Failed to create node " f"{node_id}: {e}")

    for edge in edges:

        if not isinstance(edge, dict):
            continue

        source = edge.get("source")

        target = edge.get("target")

        relationship = edge.get("rel", "RELATED_TO")

        if not source or not target:
            continue

        if str(source) not in valid_node_ids or str(target) not in valid_node_ids:

            print(f"Skipping edge: " f"{source} -> {target}")

            continue

        relationship = re.sub(r"[^a-zA-Z0-9_]", "_", str(relationship))

        if not relationship:
            relationship = "RELATED_TO"

        try:

            graph.query(
                f"""
                MATCH (
                    a {{name: $source}}
                ),
                (
                    b {{name: $target}}
                )

                MERGE (
                    a
                )-[:`{relationship}`]->(
                    b
                )
                """,
                {
                    "source": str(source),
                    "target": str(target),
                },
            )

        except Exception as e:

            print(f"Failed to create relationship " f"{source} -> {target}: {e}")

    try:

        graph.query(
            """
            MERGE (
                d:Document
                {name: $name}
            )
            """,
            {"name": filename},
        )

    except Exception as e:

        print(f"Failed to create document node: {e}")

    print(f"Knowledge graph updated successfully " f"for {filename}")


async def run_vector_fallback(query_text: str):

    query_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2-preview",
        task_type="retrieval_query",
        rate_limiter=rate_limiter,
    )

    vector_store = QdrantVectorStore(
        client=q_client,
        collection_name=COLLECTION_NAME,
        embedding=query_embeddings,
    )

    docs = vector_store.similarity_search(query_text, k=3)

    context = "\n\n".join(d.page_content for d in docs if d.page_content)

    if not context:

        return {"answer": "No relevant info found."}

    prompt = f"""
Answer the question using ONLY the provided context.

If the answer cannot be found in the context,
say that there is not enough information.

Context:

{context}

Question:

{query_text}
"""

    response = await llm.ainvoke(prompt)

    return {"answer": response.content}
