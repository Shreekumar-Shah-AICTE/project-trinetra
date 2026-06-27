"""
semantic.py — Lightweight TF-IDF Semantic Layer for Project Trinetra (त्रिनेत्र)

Adds a local, CPU-only, deterministic semantic signal using scikit-learn's
TfidfVectorizer. This catches candidates who describe good work in natural
language without using exact JD keywords.

Design constraints:
- No hosted APIs, no network calls
- No sentence-transformers, no torch
- No GPU
- Deterministic output
- Runs within 5-minute budget on 100K candidates
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.jd import CORE_CONCEPTS, PREFERRED_CONCEPTS, GENERAL_AI_CONCEPTS, PRODUCTION_KEYWORDS


def build_jd_query() -> str:
    """
    Build a synthetic query string from the JD's core concepts.
    This represents "what the ideal candidate looks like" in text form.
    Includes synonym clusters to catch candidates who write about technologies
    using adjacent industry terminology.
    """
    query_parts = []
    
    # Core concepts appear 3x (highest importance)
    for concept in CORE_CONCEPTS:
        query_parts.extend([concept] * 3)
    
    # Preferred concepts appear 2x
    for concept in PREFERRED_CONCEPTS:
        query_parts.extend([concept] * 2)
    
    # General AI concepts appear 1x
    for concept in GENERAL_AI_CONCEPTS:
        query_parts.append(concept)
    
    # Production keywords appear 2x
    for concept in PRODUCTION_KEYWORDS:
        query_parts.extend([concept] * 2)
        
    # Synonym expansions to capture adjacent terms (semantic bridge)
    synonym_clusters = [
        # Vector search synonyms
        "vector database dense retrieval vector search similarity search approximate nearest neighbor ann index",
        # Embedding synonyms
        "dense vector representation sentence embedding text embeddings sentence transformers model",
        # Re-ranking synonyms
        "cross encoder bi encoder reranking reranker learning to rank learning-to-rank ltr xgboost lightgbm model",
        # Hybrid retrieval synonyms
        "hybrid search hybrid retrieval reciprocal rank fusion rrf lexical dense fusion bm25 tfidf search relevance",
        # Evaluation synonyms
        "search evaluation relevance evaluation offline evaluation ndcg mrr map precision recall f1 ranking benchmarks",
        # Production scaling
        "production deployment scalable pipeline low latency high throughput api integration docker kubernetes aws microservices",
    ]
    
    # Repeat clusters 2x for weight
    for cluster in synonym_clusters:
        query_parts.extend([cluster] * 2)
    
    # Add key phrases from the JD
    jd_phrases = [
        "embeddings based retrieval systems deployed to real users",
        "vector databases hybrid search infrastructure",
        "evaluation frameworks ranking systems ndcg mrr map",
        "shipped end to end ranking search recommendation system",
        "production experience embeddings retrieval ranking",
        "product company AI engineer founding team",
        "candidate matching semantic search relevance",
    ]
    query_parts.extend(jd_phrases)
    
    return " ".join(query_parts)


def compute_semantic_scores(
    candidate_texts: list[str],
    candidate_ids: list[str],
    max_features: int = 8000,
) -> dict[str, float]:
    """
    Compute TF-IDF cosine similarity between each candidate's full text
    and the synthetic JD query.
    
    Returns {candidate_id: semantic_score (0-1)}.
    """
    if not candidate_texts:
        return {}
    
    # Build query
    jd_query = build_jd_query()
    
    # Combine query + all candidates for fitting
    all_texts = [jd_query] + candidate_texts
    
    # Fit TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),  # Unigrams + bigrams (e.g., "vector search")
        min_df=2,  # Skip terms appearing in only 1 document
        max_df=0.95,  # Skip terms appearing in >95% of docs
        sublinear_tf=True,  # Apply log normalization to term frequency
    )
    
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Query vector is first row
    query_vector = tfidf_matrix[0:1]
    candidate_vectors = tfidf_matrix[1:]
    
    # Compute cosine similarity (batch — fast)
    similarities = cosine_similarity(query_vector, candidate_vectors).flatten()
    
    # Map to candidate IDs
    scores = {}
    for cid, sim in zip(candidate_ids, similarities):
        scores[cid] = float(sim)
    
    return scores
