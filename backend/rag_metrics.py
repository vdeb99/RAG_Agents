
"""
RAG Retrieval Evaluation Metrics

Provides lightweight metrics to evaluate the quality
of document retrieval in a RAG pipeline.
"""


def precision_at_k(retrieved, relevant, k=5):
    """Calculate the fraction of relevant documents in top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    results = retrieved[:k]

    if not results:
        return 0.0

    relevant_set = set(relevant)
    hits = sum(1 for doc in results if doc in relevant_set)

    return hits / len(results)


def recall_at_k(retrieved, relevant, k=5):
    """Calculate relevant documents retrieved in top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    relevant_set = set(relevant)

    if not relevant_set:
        return 0.0

    hits = sum(
        1 for doc in retrieved[:k]
        if doc in relevant_set
    )

    return hits / len(relevant_set)


def mean_reciprocal_rank(retrieved, relevant):
    """Calculate reciprocal rank of the first relevant result."""
    relevant_set = set(relevant)

    for rank, doc in enumerate(retrieved, start=1):
        if doc in relevant_set:
            return 1 / rank

    return 0.0


def hit_rate(retrieved, relevant):
    """Check whether at least one relevant document was retrieved."""
    relevant_set = set(relevant)

    return float(any(doc in relevant_set for doc in retrieved))


def evaluate_retrieval(retrieved, relevant, k=5):
    """Generate a complete retrieval evaluation report."""
    return {
        "precision_at_k": round(
            precision_at_k(retrieved, relevant, k), 4
        ),
        "recall_at_k": round(
            recall_at_k(retrieved, relevant, k), 4
        ),
        "mean_reciprocal_rank": round(
            mean_reciprocal_rank(retrieved, relevant), 4
        ),
        "hit_rate": round(
            hit_rate(retrieved, relevant), 4
        )
    }


if __name__ == "__main__":
    retrieved_docs = ["doc_1", "doc_3", "doc_2", "doc_5"]
    relevant_docs = ["doc_1", "doc_2", "doc_4"]

    report = evaluate_retrieval(
        retrieved_docs,
        relevant_docs,
        k=3
    )

    print("RAG Retrieval Evaluation")
    for metric, score in report.items():
        print(f"{metric}: {score}")
