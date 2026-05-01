# Literature Survey

## Paper: *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity*

### Key Insights & Implementation

1. Recent research shows that traditional “static RAG” systems using fixed top-K retrieval are insufficient for handling complex enterprise-level queries and multi-hop reasoning tasks.

2. The paper introduces an **Adaptive Retrieval-Augmented Generation (Adaptive-RAG)** framework where the retrieval strategy dynamically changes based on query complexity instead of relying on a single retrieval pipeline.

3. Modern RAG systems combine:
   - semantic vector retrieval,
   - graph traversal,
   - multi-hop reasoning,
   - and adaptive context selection  
   to improve factual grounding and retrieval precision.

4. The research emphasizes that lightweight queries should use efficient vector retrieval, while complex relationship-heavy queries should trigger deeper reasoning workflows and structured graph traversal.

5. **Application in Our Project:**  
   Our implementation follows a hybrid retrieval architecture that intelligently combines:
   - **Neo4j** for structured relationship-aware retrieval, and
   - **Qdrant** for semantic similarity-based vector search.

6. The system first attempts graph traversal for entity-connected queries and falls back to vector retrieval when direct graph relationships are unavailable.

7. This adaptive retrieval workflow improves:
   - contextual relevance,
   - retrieval accuracy,
   - scalability,
   - and response grounding.

8. The paper’s concept of dynamically selecting retrieval strategies directly influenced our modular retrieval orchestration pipeline and backend architecture.

### Reference

- Jeong et al., *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity*  
- arXiv: https://arxiv.org/abs/2403.14403

---

# Conclusion

The literature survey highlights the growing importance of adaptive and hybrid retrieval architectures in modern RAG systems. Inspired by these research directions, our project integrates:
- graph-based retrieval using Neo4j,
- semantic vector search using Qdrant,
- adaptive retrieval routing,
- and context-grounded response generation  
to build a scalable and efficient Agentic RAG framework.