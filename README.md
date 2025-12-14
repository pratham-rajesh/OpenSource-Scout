# 🔍 OpenSource Scout v2.0

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.4-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent AI-powered platform that helps developers discover the perfect open-source issues to contribute to, based on their skills, experience, and interests. Built with advanced RAG (Retrieval Augmented Generation) and KDD (Knowledge Discovery in Databases) pipelines.

## 📺 Demo & Presentation

- **🎥 Video Demo**: [Watch Demo](https://youtu.be/5SUX6wNTbm8)
- **📊 Presentation Slides**: [View Slides](https://docs.google.com/presentation/d/1DlbIibuHeVliemwHJqZrA1hAd8dmhdL9bnmG9UbYSyw/edit?usp=sharing)


---

## 🌟 Key Features

### 🎯 Intelligent Issue Recommendations
- **Personalized Matching** - AI analyzes your GitHub profile, skills, and contribution history
- **Difficulty Estimation** - Automatically estimates issue complexity based on multiple factors
- **Smart Filtering** - Filters by language, repository stars, and issue freshness
- **Context-Aware** - Considers your past contributions and learning goals

### 🤖 AI-Powered Chatbot
- **Natural Conversations** - Chat naturally about your interests and get recommendations
- **RAG-Enhanced** - Uses ChromaDB vector database for accurate, context-aware responses
- **Intent Classification** - Understands what you're looking for (recommendations, help, info)
- **Conversation Memory** - Maintains context across multiple messages
- **Groq Integration** - Ultra-fast responses using Llama 3.3 70B

### 📊 KDD Pipeline (Knowledge Discovery)
- **Data Collection** - Fetches issues from GitHub API with rate limiting
- **Data Cleaning** - Removes duplicates, filters spam, normalizes data
- **Feature Engineering** - Extracts meaningful features for ML models
- **Pattern Discovery** - Identifies trends in successful contributions
- **N-Fold Cross-Validation** - Rigorous testing of recommendation quality

### 👤 User Management
- **Secure Authentication** - Login/signup with password hashing
- **GitHub Integration** - Link your GitHub account for personalized recommendations
- **Profile Management** - Track your skills, interests, and solved issues
- **Contribution History** - Keep track of issues you've worked on

### 📈 Analytics & Insights
- **Skill Tracking** - Monitor your proficiency in different technologies
- **PR Statistics** - View your contribution metrics
- **Issue Difficulty Analysis** - Understand complexity patterns
- **Recommendation Quality Metrics** - See how well recommendations match your profile

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask Web App                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Auth       │  │   GitHub     │  │   AI Chatbot         │  │
│  │   System     │  │   Helper     │  │   (Groq + RAG)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              KDD Pipeline                                 │  │
│  │  Data Collection → Cleaning → Feature Engineering        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   RAG        │  │   ChromaDB   │  │   SQLite Database    │  │
│  │   Engine     │  │   Vectors    │  │   (User Data)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.8+
GitHub Personal Access Token
Groq API Key (free)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/opensource-scout.git
cd opensource-scout
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# GitHub API
GITHUB_TOKEN=your_github_token_here

# Groq API (for chatbot)
GROQ_API_KEY=your_groq_api_key_here

# Flask Secret Key
SECRET_KEY=your_secret_key_here
```

5. **Initialize database**
```bash
python migrate_db.py
```

6. **Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` in your browser!

---

## 📖 How to Use

### 1. Create an Account
- Sign up with email and password
- Link your GitHub username
- System analyzes your GitHub profile

### 2. Get Recommendations
- **Dashboard**: View personalized issue recommendations
- **Filters**: Adjust by language, difficulty, stars
- **Details**: Click on issues to see full context

### 3. Chat with AI
- **Ask Questions**: "Find me Python issues for beginners"
- **Get Advice**: "What skills should I learn next?"
- **Explore**: "Show me trending repositories"

### 4. Track Progress
- Mark issues as solved
- Update your skills
- View contribution statistics

---

## 🛠️ Technical Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Flask 3.0 | HTTP server and routing |
| **Database** | SQLite + SQLAlchemy | User data persistence |
| **Authentication** | Flask-Login + Werkzeug | Secure user sessions |
| **GitHub API** | Requests | Fetch issues and user data |

### AI & ML
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Groq (Llama 3.3 70B) | Chatbot responses |
| **Vector DB** | ChromaDB | RAG knowledge base |
| **Embeddings** | OpenAI/Groq | Semantic search |
| **KDD Pipeline** | Custom Python | Data mining & feature extraction |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Templates** | Jinja2 | Dynamic HTML rendering |
| **Styling** | CSS3 | Modern, responsive design |
| **JavaScript** | Vanilla JS | Interactive UI elements |

---

## 📊 KDD Pipeline Details

### 1. Data Collection
```python
# Fetch issues from GitHub API
issues = search_good_first_issues(
    languages=user_languages,
    min_stars=10,
    max_age_days=90
)
```

### 2. Data Cleaning
- Remove duplicate issues
- Filter out spam/invalid issues
- Normalize text fields
- Handle missing values

### 3. Feature Engineering
```python
features = {
    'difficulty_score': estimate_difficulty(issue),
    'language_match': calculate_language_match(user, issue),
    'repo_popularity': get_repo_stars(issue),
    'issue_freshness': calculate_age(issue),
    'label_relevance': match_labels(user_skills, issue_labels)
}
```

### 4. Recommendation Scoring
```python
score = (
    0.3 * difficulty_match +
    0.25 * language_match +
    0.2 * repo_popularity +
    0.15 * issue_freshness +
    0.1 * label_relevance
)
```

---

## 🤖 Chatbot Architecture

### RAG (Retrieval Augmented Generation)

```python
# 1. User asks a question
user_query = "Find me beginner Python issues"

# 2. Retrieve relevant context from ChromaDB
context = chroma_db.query(
    query_texts=[user_query],
    n_results=5
)

# 3. Build prompt with context
prompt = f"""
Context: {context}
User Profile: {user_skills}
Question: {user_query}

Provide personalized recommendations.
"""

# 4. Generate response with Groq
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}]
)
```

### Intent Classification
- **RECOMMENDATION**: User wants issue suggestions
- **HELP**: User needs guidance
- **INFO**: User wants to learn about the platform
- **CHAT**: General conversation

---

## 📁 Project Structure

```
opensource-scout/
│
├── app.py                          # Main Flask application
├── auth.py                         # Authentication logic
├── models.py                       # Database models
├── github_helper.py                # GitHub API integration
├── kdd_process.py                  # KDD pipeline
├── feature_engineering.py          # ML feature extraction
├── rag_engine.py                   # RAG system
├── testing.py                      # N-fold cross-validation
│
├── chatbot/                        # AI Chatbot module
│   ├── chatbot_service.py         # Main chatbot logic
│   ├── conversation_manager.py    # Conversation state
│   ├── intent_classifier.py       # Intent detection
│   └── prompts.py                 # LLM prompts
│
├── templates/                      # HTML templates
│   ├── index.html                 # Landing page
│   ├── login.html                 # Login page
│   ├── signup.html                # Signup page
│   ├── dashboard.html             # Main dashboard
│   ├── profile.html               # User profile
│   └── chat.html                  # Chatbot interface
│
├── static/                         # CSS, JS, images
├── config/                         # Configuration files
├── instance/                       # SQLite database
├── chroma_db/                      # ChromaDB vector store
│
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

---

## 🔑 API Keys Setup

### GitHub Personal Access Token
1. Go to [GitHub Settings → Developer Settings → Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:user`, `user:email`
4. Copy token and add to `.env`

### Groq API Key
1. Visit [Groq Console](https://console.groq.com/)
2. Sign up for free account
3. Generate API key
4. Copy key and add to `.env`

---

## 🧪 Testing

### Run N-Fold Cross-Validation
```bash
python testing.py
```

This will:
- Split data into N folds
- Train recommendation model on each fold
- Calculate precision, recall, F1-score
- Generate performance report

### Test Chatbot
```bash
python test_chatbot.py
```

### Test Individual Components
```bash
python test_conversation_manager.py
python test_intent_classifier.py
```

---

## 📈 Performance Metrics

### Recommendation Quality
- **Precision**: % of recommended issues that are relevant
- **Recall**: % of relevant issues that are recommended
- **F1-Score**: Harmonic mean of precision and recall
- **User Satisfaction**: Based on solved issues

### Chatbot Performance
- **Response Time**: < 2 seconds (with Groq)
- **Intent Accuracy**: ~85% correct classification
- **Context Retention**: Maintains 5 previous messages
- **Relevance Score**: Measured via user feedback

---

## 🎯 Use Cases

### For Beginners
- Find "good first issue" labeled problems
- Get issues matched to your skill level
- Learn new technologies through practice
- Build contribution history

### For Experienced Developers
- Discover challenging issues in your expertise
- Contribute to high-impact projects
- Expand into new technology stacks
- Mentor others through issue recommendations

### For Open Source Maintainers
- Help contributors find suitable issues
- Improve issue labeling and organization
- Understand contributor skill distribution
- Increase project engagement

---

## 🔒 Security & Privacy

- **Password Hashing**: Werkzeug secure password hashing
- **Session Management**: Flask-Login secure sessions
- **API Rate Limiting**: Respects GitHub API limits
- **Data Privacy**: User data stored locally in SQLite
- **No Data Sharing**: Your GitHub data stays private

---

## 🚧 Roadmap

### v2.1 (Upcoming)
- [ ] Multi-language support
- [ ] Advanced skill assessment
- [ ] Team collaboration features
- [ ] Mobile-responsive design improvements

### v3.0 (Future)
- [ ] Machine learning recommendation model
- [ ] Integration with more Git platforms (GitLab, Bitbucket)
- [ ] Gamification and achievements
- [ ] Community features and forums

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/YOUR_USERNAME)

---

## 🙏 Acknowledgments

- **GitHub API** - For providing comprehensive repository data
- **Groq** - For ultra-fast LLM inference
- **ChromaDB** - For efficient vector storage and retrieval
- **Flask Community** - For excellent web framework
- **Open Source Community** - For inspiration and support

---

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/opensource-scout/issues)
- **Email**: your.email@example.com
- **Twitter**: [@YourTwitter](https://twitter.com/YOUR_HANDLE)

---

## 🌟 Star History

If you find this project useful, please consider giving it a ⭐!

[![Star History Chart](https://api.star-history.com/svg?repos=YOUR_USERNAME/opensource-scout&type=Date)](https://star-history.com/#YOUR_USERNAME/opensource-scout&Date)

---

<div align="center">
  <p>Made with ❤️ by developers, for developers</p>
  <p>Happy Contributing! 🚀</p>
</div>
