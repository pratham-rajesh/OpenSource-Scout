"""
RAG Engine
==========
RAG = Retrieval Augmented Generation

How it works:
1. Store solved issues as "embeddings" (vectors) in ChromaDB
2. When user asks for recommendations, search similar issues
3. Feed similar issues + new issues to GPT
4. GPT gives better recommendations based on user's history

Think of it like:
- "You solved these Python issues before"
- "Here's a similar one you might like"
"""

import os
import json
from openai import OpenAI

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("ChromaDB not installed. RAG will use fallback mode.")


class RAGEngine:
    """
    Retrieval Augmented Generation engine for recommendations.
    
    Uses:
    - ChromaDB: Vector database to store/search issue embeddings
    - OpenAI: Generate embeddings and recommendations
    """
    
    def __init__(self, persist_directory="./chroma_db"):
        """Initialize RAG engine."""
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.openai_client = None
        
        # Initialize ChromaDB if available
        if CHROMA_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=persist_directory)
                self.collection = self.client.get_or_create_collection(
                    name="solved_issues",
                    metadata={"description": "User's solved issues for RAG"}
                )
                print("ChromaDB initialized successfully")
            except Exception as e:
                print(f"ChromaDB initialization failed: {e}")
                self.client = None
        
        # Initialize OpenAI if key exists
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def add_solved_issue(self, user_id, issue_data):
        """
        Add a solved issue to the vector database.
        
        Parameters:
        - user_id: The user who solved it
        - issue_data: Dict with issue_title, repo_name, language, difficulty, notes
        """
        if not self.collection:
            return False
        
        try:
            # Create a text representation of the issue
            text = f"""
            Issue: {issue_data.get('issue_title', '')}
            Repository: {issue_data.get('repo_name', '')}
            Language: {issue_data.get('language', '')}
            Difficulty: {issue_data.get('difficulty_rating', 'unknown')}/5
            Notes: {issue_data.get('user_notes', '')}
            """
            
            # Unique ID for this entry
            doc_id = f"user_{user_id}_issue_{issue_data.get('issue_url', '')}"
            
            # Add to ChromaDB (it automatically creates embeddings)
            self.collection.add(
                documents=[text],
                metadatas=[{
                    "user_id": str(user_id),
                    "language": issue_data.get('language', ''),
                    "difficulty": str(issue_data.get('difficulty_rating', 3)),
                    "repo": issue_data.get('repo_name', '')
                }],
                ids=[doc_id]
            )
            return True
            
        except Exception as e:
            print(f"Error adding issue to RAG: {e}")
            return False
    
    def find_similar_issues(self, user_id, query_text, n_results=5):
        """
        Find issues similar to the query from user's history.
        
        Parameters:
        - user_id: Filter to only this user's issues
        - query_text: Text to search for (e.g., "Python web development")
        - n_results: How many similar issues to return
        """
        if not self.collection:
            return []
        
        try:
            # Search for similar documents
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"user_id": str(user_id)}
            )
            
            return results.get('documents', [[]])[0]
            
        except Exception as e:
            print(f"Error searching RAG: {e}")
            return []
    
    def get_user_patterns(self, user_id):
        """
        Analyze user's solved issues to find patterns.
        
        Returns insights like:
        - Preferred languages
        - Average difficulty tackled
        - Common repos/topics
        """
        if not self.collection:
            return None
        
        try:
            # Get all issues for this user
            results = self.collection.get(
                where={"user_id": str(user_id)}
            )
            
            if not results or not results.get('metadatas'):
                return None
            
            metadatas = results['metadatas']
            
            # Analyze patterns
            languages = {}
            difficulties = []
            repos = {}
            
            for meta in metadatas:
                # Count languages
                lang = meta.get('language', 'Unknown')
                languages[lang] = languages.get(lang, 0) + 1
                
                # Collect difficulties
                diff = meta.get('difficulty')
                if diff:
                    try:
                        difficulties.append(int(diff))
                    except:
                        pass
                
                # Count repos
                repo = meta.get('repo', 'Unknown')
                repos[repo] = repos.get(repo, 0) + 1
            
            return {
                "total_solved": len(metadatas),
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3],
                "avg_difficulty": round(sum(difficulties) / len(difficulties), 1) if difficulties else 0,
                "top_repos": sorted(repos.items(), key=lambda x: x[1], reverse=True)[:3]
            }
            
        except Exception as e:
            print(f"Error getting patterns: {e}")
            return None
    
    def get_rag_recommendations(self, user_id, new_issues, user_languages):
        """
        Get AI recommendations using RAG.
        
        1. Find similar issues from user's history
        2. Combine with new issues
        3. Ask GPT for personalized recommendations
        """
        if not self.openai_client:
            return self._fallback_recommendations(new_issues)
        
        # Get user's patterns
        patterns = self.get_user_patterns(user_id)
        
        # Get similar past issues
        search_query = " ".join([lang[0] if isinstance(lang, tuple) else lang for lang in user_languages[:3]])
        similar_past = self.find_similar_issues(user_id, search_query, n_results=5)
        
        # Build context for GPT
        context = "User's history:\n"
        if patterns:
            context += f"- Solved {patterns['total_solved']} issues\n"
            context += f"- Top languages: {patterns['top_languages']}\n"
            context += f"- Average difficulty: {patterns['avg_difficulty']}/5\n"
        else:
            context += "- New user, no history yet\n"
        
        if similar_past:
            context += "\nPreviously solved similar issues:\n"
            for issue in similar_past[:3]:
                context += f"- {issue[:100]}...\n"
        
        # Prepare new issues for GPT
        issues_text = "\n".join([
            f"{i+1}. [{issue['repo']}] {issue['title']} (Language: {issue['language']})"
            for i, issue in enumerate(new_issues[:10])
        ])
        
        prompt = f"""You are an open-source contribution advisor.

{context}

Here are new "good first issues" available:
{issues_text}

Based on the user's history and skills, recommend the TOP 5 best issues for them.
For each, explain:
1. Why it matches their experience
2. What they'll learn
3. Difficulty (Easy/Medium/Hard)

Return as JSON:
{{
    "recommendations": [
        {{
            "issue_index": 0,
            "match_reason": "...",
            "learning": "...",
            "difficulty": "Easy"
        }}
    ],
    "advice": "One personalized tip"
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
            
            # Match recommendations to actual issues
            recommendations = []
            for rec in result.get("recommendations", [])[:5]:
                idx = rec.get("issue_index", 0)
                if 0 <= idx < len(new_issues):
                    issue = new_issues[idx].copy()
                    issue["ai_match_reason"] = rec.get("match_reason", "")
                    issue["ai_learning"] = rec.get("learning", "")
                    issue["ai_difficulty"] = rec.get("difficulty", "Medium")
                    recommendations.append(issue)
            
            return {
                "recommendations": recommendations,
                "advice": result.get("advice", "Keep contributing!"),
                "user_patterns": patterns
            }
            
        except Exception as e:
            print(f"RAG recommendation error: {e}")
            return self._fallback_recommendations(new_issues)
    
    def _fallback_recommendations(self, issues):
        """Fallback when AI is not available."""
        recommendations = []
        for issue in issues[:5]:
            issue_copy = issue.copy()
            issue_copy["ai_match_reason"] = f"Matches your {issue.get('language', 'programming')} skills"
            issue_copy["ai_learning"] = "Open source contribution experience"
            issue_copy["ai_difficulty"] = "Beginner-friendly"
            recommendations.append(issue_copy)
        
        return {
            "recommendations": recommendations,
            "advice": "Start with issues in languages you know!",
            "user_patterns": None
        }


# Global RAG engine instance
rag_engine = None

def get_rag_engine():
    """Get or create the global RAG engine."""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine
