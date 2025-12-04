"""
KDD Process Module
==================
Implements Knowledge Discovery in Databases (KDD) pipeline:
1. Selection - Selecting relevant data
2. Preprocessing - Cleaning and transforming data
3. Transformation - Feature extraction
4. Data Mining - Applying algorithms
5. Interpretation - Evaluating results
"""

import re
from collections import Counter


class KDDPipeline:
    """
    Knowledge Discovery in Databases (KDD) Pipeline.
    Processes raw GitHub data into actionable recommendations.
    """
    
    def __init__(self):
        self.raw_data = None
        self.cleaned_data = None
        self.features = None
        self.results = None
    
    # =========================================
    # STEP 1: SELECTION
    # =========================================
    def select_data(self, issues, user_languages):
        """
        Selection phase: Extracting relevant data from source.
        Filters issues based on user's known languages.
        """
        # Storing raw data
        self.raw_data = {
            'issues': issues,
            'user_languages': user_languages,
            'total_issues': len(issues),
            'total_languages': len(user_languages)
        }
        
        # Selecting issues that match user languages
        lang_names = [l[0] if isinstance(l, tuple) else l for l in user_languages]
        
        selected_issues = []
        for issue in issues:
            issue_lang = issue.get('language', '')
            if issue_lang in lang_names or issue_lang == 'Any' or not issue_lang:
                selected_issues.append(issue)
        
        # Logging selection statistics
        selection_stats = {
            'input_count': len(issues),
            'selected_count': len(selected_issues),
            'selection_ratio': len(selected_issues) / len(issues) if issues else 0
        }
        
        return selected_issues, selection_stats
    
    # =========================================
    # STEP 2: PREPROCESSING
    # =========================================
    def preprocess_data(self, issues):
        """
        Preprocessing phase: Cleaning and normalizing data.
        Handles missing values and standardizes text.
        """
        cleaned_issues = []
        
        for issue in issues:
            # Handling missing values
            cleaned = {
                'title': issue.get('title', 'Untitled').strip(),
                'repo': issue.get('repo', 'Unknown'),
                'url': issue.get('url', ''),
                'language': issue.get('language', 'Unknown'),
                'labels': issue.get('labels', []),
                'body': issue.get('body', ''),
                'comments': issue.get('comments', 0)
            }
            
            # Normalizing text - lowercase for consistency
            cleaned['title_normalized'] = cleaned['title'].lower()
            cleaned['body_normalized'] = cleaned['body'].lower() if cleaned['body'] else ''
            
            # Removing special characters from title
            cleaned['title_clean'] = re.sub(r'[^\w\s]', '', cleaned['title_normalized'])
            
            # Handling empty labels
            if not cleaned['labels']:
                cleaned['labels'] = ['untagged']
            
            cleaned_issues.append(cleaned)
        
        self.cleaned_data = cleaned_issues
        
        # Logging preprocessing statistics
        preprocess_stats = {
            'processed_count': len(cleaned_issues),
            'missing_titles': sum(1 for i in issues if not i.get('title')),
            'missing_bodies': sum(1 for i in issues if not i.get('body')),
            'missing_labels': sum(1 for i in issues if not i.get('labels'))
        }
        
        return cleaned_issues, preprocess_stats
    
    # =========================================
    # STEP 3: TRANSFORMATION
    # =========================================
    def transform_data(self, issues, user_languages):
        """
        Transformation phase: Feature extraction and engineering.
        Converts raw data into feature vectors.
        """
        features_list = []
        
        # Creating language proficiency map
        lang_proficiency = {}
        for i, lang in enumerate(user_languages):
            lang_name = lang[0] if isinstance(lang, tuple) else lang
            lang_count = lang[1] if isinstance(lang, tuple) else 1
            lang_proficiency[lang_name] = {
                'rank': i + 1,
                'repo_count': lang_count,
                'proficiency_score': max(1, 10 - i) * lang_count
            }
        
        for issue in issues:
            feature_vector = {}
            
            # Feature 1: Language match score
            issue_lang = issue.get('language', 'Unknown')
            if issue_lang in lang_proficiency:
                feature_vector['language_match'] = lang_proficiency[issue_lang]['proficiency_score']
                feature_vector['language_rank'] = lang_proficiency[issue_lang]['rank']
            else:
                feature_vector['language_match'] = 0
                feature_vector['language_rank'] = 99
            
            # Feature 2: Difficulty score based on labels
            feature_vector['difficulty_score'] = self._calculate_difficulty(issue)
            
            # Feature 3: Complexity score based on body length
            body_len = len(issue.get('body', '') or '')
            feature_vector['complexity_score'] = min(5, body_len // 200)
            
            # Feature 4: Engagement score based on comments
            comments = issue.get('comments', 0)
            feature_vector['engagement_score'] = min(5, comments // 2)
            
            # Feature 5: Label count
            feature_vector['label_count'] = len(issue.get('labels', []))
            
            # Feature 6: Title length (shorter = usually simpler)
            title_len = len(issue.get('title', ''))
            feature_vector['title_complexity'] = min(5, title_len // 20)
            
            # Feature 7: Has beginner-friendly labels
            beginner_labels = ['good first issue', 'beginner', 'easy', 'starter', 'first-timers-only']
            issue_labels = [l.lower() for l in issue.get('labels', [])]
            feature_vector['beginner_friendly'] = 1 if any(bl in issue_labels for bl in beginner_labels) else 0
            
            # Combining features with issue data
            feature_vector['issue_data'] = issue
            features_list.append(feature_vector)
        
        self.features = features_list
        
        # Logging transformation statistics
        transform_stats = {
            'features_extracted': 7,
            'samples_transformed': len(features_list),
            'avg_difficulty': sum(f['difficulty_score'] for f in features_list) / len(features_list) if features_list else 0
        }
        
        return features_list, transform_stats
    
    def _calculate_difficulty(self, issue):
        """
        Calculating difficulty score from issue attributes.
        Returns score from 1 (easy) to 5 (hard).
        """
        labels = [l.lower() for l in issue.get('labels', [])]
        title = issue.get('title', '').lower()
        
        difficulty = 3  # Default: medium
        
        # Easy indicators
        easy_terms = ['typo', 'documentation', 'docs', 'readme', 'beginner', 
                      'easy', 'simple', 'minor', 'small', 'first-timer']
        for term in easy_terms:
            if term in labels or term in title:
                difficulty -= 1
                break
        
        # Hard indicators
        hard_terms = ['complex', 'refactor', 'architecture', 'performance', 
                      'security', 'breaking', 'major', 'difficult', 'advanced']
        for term in hard_terms:
            if term in labels or term in title:
                difficulty += 1
                break
        
        # Clamping to valid range
        return max(1, min(5, difficulty))
    
    # =========================================
    # STEP 4: DATA MINING
    # =========================================
    def mine_data(self, features, top_n=10):
        """
        Data Mining phase: Applying recommendation algorithm.
        Uses content-based filtering with weighted scoring.
        """
        # Defining feature weights
        weights = {
            'language_match': 0.35,      # Most important: language match
            'beginner_friendly': 0.25,   # Beginner-friendly labels
            'difficulty_score': -0.15,   # Lower difficulty preferred (negative weight)
            'complexity_score': -0.10,   # Lower complexity preferred
            'engagement_score': 0.10,    # Some engagement is good
            'language_rank': -0.05       # Primary language preferred
        }
        
        # Calculating recommendation scores
        scored_items = []
        for feature in features:
            score = 0
            for feat_name, weight in weights.items():
                feat_value = feature.get(feat_name, 0)
                score += weight * feat_value
            
            scored_items.append({
                'score': score,
                'features': feature,
                'issue': feature['issue_data']
            })
        
        # Sorting by score descending
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        # Selecting top N recommendations
        top_recommendations = scored_items[:top_n]
        
        self.results = top_recommendations
        
        # Logging mining statistics
        mining_stats = {
            'algorithm': 'Content-Based Filtering',
            'total_scored': len(scored_items),
            'top_n_selected': len(top_recommendations),
            'score_range': {
                'max': max(s['score'] for s in scored_items) if scored_items else 0,
                'min': min(s['score'] for s in scored_items) if scored_items else 0,
                'avg': sum(s['score'] for s in scored_items) / len(scored_items) if scored_items else 0
            }
        }
        
        return top_recommendations, mining_stats
    
    # =========================================
    # STEP 5: INTERPRETATION
    # =========================================
    def interpret_results(self, recommendations):
        """
        Interpretation phase: Evaluating and explaining results.
        Generates human-readable insights.
        """
        if not recommendations:
            return {
                'summary': 'No recommendations generated',
                'insights': [],
                'quality_score': 0
            }
        
        # Analyzing recommendation quality
        scores = [r['score'] for r in recommendations]
        avg_score = sum(scores) / len(scores)
        
        # Extracting language distribution
        languages = [r['issue'].get('language', 'Unknown') for r in recommendations]
        lang_distribution = Counter(languages)
        
        # Extracting difficulty distribution
        difficulties = [r['features']['difficulty_score'] for r in recommendations]
        avg_difficulty = sum(difficulties) / len(difficulties)
        
        # Generating insights
        insights = []
        
        # Insight 1: Language focus
        top_lang = lang_distribution.most_common(1)[0] if lang_distribution else ('Unknown', 0)
        insights.append(f"Primary language focus: {top_lang[0]} ({top_lang[1]} issues)")
        
        # Insight 2: Difficulty assessment
        if avg_difficulty <= 2:
            insights.append("Difficulty level: Beginner-friendly recommendations")
        elif avg_difficulty <= 3.5:
            insights.append("Difficulty level: Intermediate recommendations")
        else:
            insights.append("Difficulty level: Advanced recommendations")
        
        # Insight 3: Diversity check
        if len(lang_distribution) > 2:
            insights.append("Good diversity across multiple languages")
        else:
            insights.append("Focused recommendations in specific languages")
        
        # Calculating quality score (0-100)
        quality_score = min(100, int(avg_score * 20 + 50))
        
        interpretation = {
            'summary': f"Generated {len(recommendations)} personalized recommendations",
            'insights': insights,
            'quality_score': quality_score,
            'statistics': {
                'avg_recommendation_score': round(avg_score, 3),
                'avg_difficulty': round(avg_difficulty, 2),
                'language_distribution': dict(lang_distribution),
                'score_distribution': {
                    'high': sum(1 for s in scores if s > avg_score),
                    'low': sum(1 for s in scores if s <= avg_score)
                }
            }
        }
        
        return interpretation
    
    # =========================================
    # FULL KDD PIPELINE
    # =========================================
    def run_pipeline(self, issues, user_languages):
        """
        Executing complete KDD pipeline.
        Returns recommendations with full statistics.
        """
        pipeline_results = {
            'steps': {},
            'recommendations': [],
            'interpretation': {}
        }
        
        # Step 1: Selection
        selected, select_stats = self.select_data(issues, user_languages)
        pipeline_results['steps']['selection'] = select_stats
        
        # Step 2: Preprocessing
        cleaned, preprocess_stats = self.preprocess_data(selected)
        pipeline_results['steps']['preprocessing'] = preprocess_stats
        
        # Step 3: Transformation
        features, transform_stats = self.transform_data(cleaned, user_languages)
        pipeline_results['steps']['transformation'] = transform_stats
        
        # Step 4: Data Mining
        recommendations, mining_stats = self.mine_data(features)
        pipeline_results['steps']['mining'] = mining_stats
        
        # Step 5: Interpretation
        interpretation = self.interpret_results(recommendations)
        pipeline_results['interpretation'] = interpretation
        
        # Formatting final recommendations
        pipeline_results['recommendations'] = [
            {
                'issue': r['issue'],
                'score': round(r['score'], 3),
                'difficulty': r['features']['difficulty_score']
            }
            for r in recommendations
        ]
        
        return pipeline_results


# Global KDD pipeline instance
kdd_pipeline = KDDPipeline()

def get_kdd_pipeline():
    """Retrieving KDD pipeline instance."""
    return kdd_pipeline
