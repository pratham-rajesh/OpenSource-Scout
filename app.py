"""
OpenSource Scout v2.0 - Main Application
========================================
Full-featured recommendation system with:
- User accounts and authentication
- KDD pipeline for data processing
- Feature engineering for ML-ready data
- RAG-based recommendations
- N-Fold cross-validation testing
- SQLite database persistence
"""

import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

# Loading environment variables
load_dotenv()

# Importing application modules
from models import db, User, SolvedIssue, UserSkill, IssueCache
from auth import create_user, verify_user, update_github_username
from github_helper import (
    get_user_info, get_user_languages, search_good_first_issues,
    get_pr_stats, estimate_issue_difficulty
)
from rag_engine import get_rag_engine
from kdd_process import get_kdd_pipeline
from feature_engineering import get_feature_engineer
from testing import get_model_tester, run_recommendation_test

# Initializing Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scout.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initializing database
db.init_app(app)

# Initializing login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    """Loading user by ID for Flask-Login."""
    return User.query.get(int(user_id))


# Creating database tables on startup
with app.app_context():
    db.create_all()


# ============================================
# PUBLIC ROUTES
# ============================================

@app.route('/')
def home():
    """Rendering home page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handling user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Verifying credentials
        user = verify_user(username, password)
        if user:
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handling user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        github_username = request.form.get('github_username', '').strip()
        
        # Validating input
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
        elif len(password) < 4:
            flash('Password must be at least 4 characters', 'error')
        else:
            # Creating user account
            user = create_user(username, password, github_username or None)
            if user:
                login_user(user)
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Username already exists', 'error')
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Logging out current user."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))


# ============================================
# PROTECTED ROUTES
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Rendering user dashboard with statistics."""
    # Querying user statistics
    solved_count = SolvedIssue.query.filter_by(user_id=current_user.id).count()
    skills = UserSkill.query.filter_by(user_id=current_user.id).all()
    recent_solved = SolvedIssue.query.filter_by(user_id=current_user.id)\
        .order_by(SolvedIssue.solved_at.desc()).limit(5).all()
    
    # Fetching GitHub statistics if connected
    github_stats = None
    if current_user.github_username:
        github_stats = get_pr_stats(current_user.github_username)
    
    return render_template('dashboard.html',
        solved_count=solved_count,
        skills=skills,
        recent_solved=recent_solved,
        github_stats=github_stats
    )


@app.route('/search')
@login_required
def search():
    """Rendering search page."""
    return render_template('search.html')


@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    """
    API endpoint for searching and recommending issues.
    Implements full KDD pipeline with feature engineering.
    """
    # Getting GitHub username from request or user profile
    github_username = request.form.get('github_username', '').strip()
    if not github_username:
        github_username = current_user.github_username
    
    if not github_username:
        return jsonify({
            'error': True,
            'message': 'Please provide a GitHub username or link your account in settings'
        })
    
    try:
        # Step 1: Fetching user profile from GitHub API
        user_info = get_user_info(github_username)
        if not user_info:
            return jsonify({
                'error': True,
                'message': f'GitHub user "{github_username}" not found'
            })
        
        # Step 2: Extracting user's programming languages
        languages = get_user_languages(github_username)
        
        # Step 3: Searching for matching issues
        issues = search_good_first_issues(languages, max_issues=30)
        
        # Step 4: Running KDD pipeline
        kdd = get_kdd_pipeline()
        kdd_results = kdd.run_pipeline(issues, languages)
        
        # Step 5: Applying feature engineering
        feature_eng = get_feature_engineer()
        feature_vectors, feature_stats = feature_eng.extract_features_batch(issues, languages)
        
        # Step 6: Getting RAG-enhanced recommendations
        rag = get_rag_engine()
        rag_result = rag.get_rag_recommendations(
            user_id=current_user.id,
            new_issues=issues,
            user_languages=languages
        )
        
        # Step 7: Filtering out already solved issues
        solved_urls = {s.issue_url for s in SolvedIssue.query.filter_by(user_id=current_user.id).all()}
        
        # Preparing recommendations with KDD scores
        kdd_recommendations = []
        for rec in kdd_results['recommendations']:
            issue = rec['issue']
            if issue['url'] not in solved_urls:
                issue['kdd_score'] = rec['score']
                issue['difficulty_estimate'] = rec['difficulty']
                kdd_recommendations.append(issue)
        
        # Merging RAG and KDD recommendations
        final_recommendations = []
        rag_recs = [r for r in rag_result['recommendations'] if r['url'] not in solved_urls]
        
        # Combining top recommendations from both methods
        seen_urls = set()
        for rec in rag_recs[:3] + kdd_recommendations[:3]:
            if rec['url'] not in seen_urls:
                seen_urls.add(rec['url'])
                final_recommendations.append(rec)
        
        # Filtering all issues
        all_issues = [i for i in issues if i['url'] not in solved_urls]
        
        return jsonify({
            'error': False,
            'user': user_info,
            'languages': languages,
            'recommendations': final_recommendations[:5],
            'all_issues': all_issues[:15],
            'advice': rag_result['advice'],
            'user_patterns': rag_result.get('user_patterns'),
            'kdd_stats': kdd_results['interpretation'],
            'feature_stats': {k: v for k, v in list(feature_stats.items())[:5]}
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({
            'error': True,
            'message': f'Error: {str(e)}'
        })


@app.route('/api/mark_solved', methods=['POST'])
@login_required
def mark_solved():
    """
    API endpoint for marking issue as solved.
    Updates user skills and adds to RAG database.
    """
    data = request.get_json()
    
    # Extracting issue data from request
    issue_url = data.get('issue_url')
    issue_title = data.get('issue_title')
    repo_name = data.get('repo_name')
    language = data.get('language')
    difficulty_rating = data.get('difficulty_rating', 3)
    user_notes = data.get('user_notes', '')
    
    # Validating required fields
    if not issue_url or not issue_title:
        return jsonify({'error': True, 'message': 'Missing issue data'})
    
    # Checking for duplicate entries
    existing = SolvedIssue.query.filter_by(
        user_id=current_user.id,
        issue_url=issue_url
    ).first()
    
    if existing:
        return jsonify({'error': True, 'message': 'Issue already marked as solved'})
    
    # Creating solved issue record
    solved = SolvedIssue(
        user_id=current_user.id,
        issue_url=issue_url,
        issue_title=issue_title,
        repo_name=repo_name,
        language=language,
        difficulty_rating=difficulty_rating,
        user_notes=user_notes
    )
    db.session.add(solved)
    
    # Updating user skill for the language
    if language:
        skill = UserSkill.query.filter_by(
            user_id=current_user.id,
            language=language
        ).first()
        
        if skill:
            # Incrementing existing skill
            skill.issues_solved += 1
            skill.skill_level = min(10, skill.skill_level + (difficulty_rating // 2))
        else:
            # Creating new skill entry
            skill = UserSkill(
                user_id=current_user.id,
                language=language,
                skill_level=difficulty_rating,
                issues_solved=1
            )
            db.session.add(skill)
    
    # Adding to RAG vector database
    rag = get_rag_engine()
    rag.add_solved_issue(current_user.id, {
        'issue_url': issue_url,
        'issue_title': issue_title,
        'repo_name': repo_name,
        'language': language,
        'difficulty_rating': difficulty_rating,
        'user_notes': user_notes
    })
    
    # Committing database changes
    db.session.commit()
    
    return jsonify({
        'error': False,
        'message': 'Issue marked as solved! Great job!'
    })


@app.route('/history')
@login_required
def history():
    """Rendering solved issues history page."""
    solved = SolvedIssue.query.filter_by(user_id=current_user.id)\
        .order_by(SolvedIssue.solved_at.desc()).all()
    return render_template('history.html', solved_issues=solved)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Handling user settings page."""
    if request.method == 'POST':
        github_username = request.form.get('github_username', '').strip()
        
        # Validating GitHub username exists
        if github_username:
            user_info = get_user_info(github_username)
            if not user_info:
                flash('GitHub username not found', 'error')
                return render_template('settings.html')
        
        # Updating user profile
        update_github_username(current_user.id, github_username or None)
        flash('Settings updated!', 'success')
    
    return render_template('settings.html')


@app.route('/api/run_tests', methods=['POST'])
@login_required
def run_tests():
    """
    API endpoint for running model validation tests.
    Executes n-fold cross-validation on recommendation model.
    """
    try:
        # Getting user's languages
        if not current_user.github_username:
            return jsonify({
                'error': True,
                'message': 'Link your GitHub account first'
            })
        
        languages = get_user_languages(current_user.github_username)
        issues = search_good_first_issues(languages, max_issues=50)
        
        if len(issues) < 10:
            return jsonify({
                'error': True,
                'message': 'Not enough issues for testing (need at least 10)'
            })
        
        # Defining recommendation function for testing
        def recommend_func(train_issues, user_langs):
            kdd = get_kdd_pipeline()
            results = kdd.run_pipeline(train_issues, user_langs)
            return [r['issue'] for r in results['recommendations']]
        
        # Running cross-validation
        tester = get_model_tester()
        test_data = [{'issue': issue, 'url': issue.get('url', '')} for issue in issues]
        
        def model_wrapper(train, test):
            train_issues = [t['issue'] for t in train]
            return recommend_func(train_issues, languages)
        
        cv_results = tester.run_cross_validation(test_data, model_wrapper, n_folds=5)
        report = tester.generate_report(cv_results)
        
        return jsonify({
            'error': False,
            'results': cv_results,
            'report': report
        })
        
    except Exception as e:
        print(f"Test error: {e}")
        return jsonify({
            'error': True,
            'message': f'Test failed: {str(e)}'
        })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'github_token': 'configured' if os.getenv('GITHUB_TOKEN') else 'not configured',
        'openai_key': 'configured' if os.getenv('OPENAI_API_KEY') else 'not configured'
    })


# ============================================
# APPLICATION ENTRY POINT
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("OpenSource Scout v2.0")
    print("=" * 50)
    print()
    print("Starting server...")
    print("Open browser: http://localhost:5000")
    print()
    print("API Keys Status:")
    print(f"  GitHub Token: {'Configured' if os.getenv('GITHUB_TOKEN') else 'Not configured'}")
    print(f"  OpenAI Key:   {'Configured' if os.getenv('OPENAI_API_KEY') else 'Not configured'}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
