"""
Get Similar Solved Issues Tool
===============================
Retrieves similar solved issues using RAG/ChromaDB.
"""

from rag_engine import get_rag_engine


def get_similar_solved(user_id, query, n_results=5):
    """
    Find similar issues from user's solved history using RAG.

    Parameters:
    - user_id: User ID
    - query: Search query text
    - n_results: Number of results to return

    Returns:
    - List of similar issue texts
    """
    try:
        rag_engine = get_rag_engine()

        # Use RAG engine's semantic search
        similar_issues = rag_engine.find_similar_issues(
            user_id=user_id,
            query_text=query,
            n_results=n_results
        )

        return similar_issues

    except Exception as e:
        print(f"Get similar solved error: {e}")
        return []
