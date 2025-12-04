"""
Feature Engineering Module
==========================
Implements advanced feature extraction for recommendation system:
- Text-based features (TF-IDF, keyword extraction)
- Numerical features (normalization, scaling)
- Categorical features (encoding)
- Derived features (combinations, ratios)
"""

import re
import math
from collections import Counter


class FeatureEngineer:
    """
    Feature Engineering pipeline for issue recommendation.
    Extracts and transforms raw data into ML-ready features.
    """
    
    def __init__(self):
        self.vocabulary = set()
        self.idf_scores = {}
        self.feature_stats = {}
    
    # =========================================
    # TEXT FEATURES
    # =========================================
    def extract_text_features(self, text):
        """
        Extracting text-based features from issue content.
        Includes keyword extraction and text statistics.
        """
        if not text:
            return {
                'word_count': 0,
                'char_count': 0,
                'avg_word_length': 0,
                'keyword_score': 0,
                'has_code_block': 0,
                'has_url': 0
            }
        
        # Tokenizing text
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Basic text statistics
        word_count = len(words)
        char_count = len(text)
        avg_word_length = sum(len(w) for w in words) / word_count if words else 0
        
        # Detecting code blocks
        has_code_block = 1 if '```' in text or '`' in text else 0
        
        # Detecting URLs
        has_url = 1 if re.search(r'https?://', text) else 0
        
        # Technical keyword scoring
        tech_keywords = ['bug', 'fix', 'feature', 'add', 'update', 'remove', 
                         'refactor', 'test', 'docs', 'style', 'performance']
        keyword_count = sum(1 for w in words if w in tech_keywords)
        keyword_score = min(5, keyword_count)
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'avg_word_length': round(avg_word_length, 2),
            'keyword_score': keyword_score,
            'has_code_block': has_code_block,
            'has_url': has_url
        }
    
    def calculate_tfidf(self, documents):
        """
        Calculating TF-IDF scores for document collection.
        Used for measuring term importance across issues.
        """
        # Building vocabulary
        doc_frequencies = Counter()
        term_frequencies = []
        
        for doc in documents:
            if not doc:
                term_frequencies.append({})
                continue
            
            words = re.findall(r'\b\w+\b', doc.lower())
            tf = Counter(words)
            term_frequencies.append(tf)
            
            # Counting document frequency
            unique_words = set(words)
            for word in unique_words:
                doc_frequencies[word] += 1
                self.vocabulary.add(word)
        
        # Calculating IDF
        n_docs = len(documents)
        for word, df in doc_frequencies.items():
            self.idf_scores[word] = math.log(n_docs / (df + 1)) + 1
        
        # Calculating TF-IDF vectors
        tfidf_vectors = []
        for tf in term_frequencies:
            tfidf = {}
            for word, freq in tf.items():
                tfidf[word] = freq * self.idf_scores.get(word, 1)
            tfidf_vectors.append(tfidf)
        
        return tfidf_vectors
    
    # =========================================
    # NUMERICAL FEATURES
    # =========================================
    def normalize_features(self, values, method='minmax'):
        """
        Normalizing numerical features to standard range.
        Supports min-max and z-score normalization.
        """
        if not values:
            return []
        
        if method == 'minmax':
            # Min-Max normalization: scales to [0, 1]
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val
            
            if range_val == 0:
                return [0.5] * len(values)
            
            normalized = [(v - min_val) / range_val for v in values]
        
        elif method == 'zscore':
            # Z-score normalization: mean=0, std=1
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_val = math.sqrt(variance) if variance > 0 else 1
            
            normalized = [(v - mean_val) / std_val for v in values]
        
        else:
            normalized = values
        
        return normalized
    
    def bin_numerical(self, value, bins=[0, 2, 5, 10, 20, float('inf')], labels=['very_low', 'low', 'medium', 'high', 'very_high']):
        """
        Converting numerical value to categorical bin.
        Useful for discretizing continuous features.
        """
        for i, (lower, upper) in enumerate(zip(bins[:-1], bins[1:])):
            if lower <= value < upper:
                return labels[i] if i < len(labels) else f'bin_{i}'
        return labels[-1] if labels else 'unknown'
    
    # =========================================
    # CATEGORICAL FEATURES
    # =========================================
    def encode_labels(self, labels):
        """
        Encoding categorical labels into numerical features.
        Uses multi-hot encoding for label lists.
        """
        # Predefined important labels
        important_labels = [
            'good first issue', 'beginner', 'easy', 'help wanted',
            'bug', 'feature', 'enhancement', 'documentation',
            'high priority', 'low priority', 'wontfix'
        ]
        
        # Creating encoding vector
        encoding = {}
        normalized_labels = [l.lower() for l in labels]
        
        for imp_label in important_labels:
            key = f'label_{imp_label.replace(" ", "_")}'
            encoding[key] = 1 if imp_label in normalized_labels else 0
        
        # Additional label statistics
        encoding['total_labels'] = len(labels)
        encoding['has_priority_label'] = 1 if any('priority' in l.lower() for l in labels) else 0
        encoding['has_type_label'] = 1 if any(t in normalized_labels for t in ['bug', 'feature', 'enhancement']) else 0
        
        return encoding
    
    def encode_language(self, language, user_languages):
        """
        Encoding programming language with user proficiency context.
        Returns match score and proficiency level.
        """
        # Creating language proficiency map
        lang_map = {}
        for i, lang in enumerate(user_languages):
            lang_name = lang[0] if isinstance(lang, tuple) else lang
            lang_count = lang[1] if isinstance(lang, tuple) else 1
            lang_map[lang_name] = {
                'rank': i + 1,
                'count': lang_count,
                'proficiency': max(1, 10 - i)
            }
        
        # Encoding issue language
        if language in lang_map:
            return {
                'language_known': 1,
                'language_rank': lang_map[language]['rank'],
                'language_proficiency': lang_map[language]['proficiency'],
                'language_repo_count': lang_map[language]['count']
            }
        else:
            return {
                'language_known': 0,
                'language_rank': 99,
                'language_proficiency': 0,
                'language_repo_count': 0
            }
    
    # =========================================
    # DERIVED FEATURES
    # =========================================
    def create_derived_features(self, issue, user_languages):
        """
        Creating derived features from combinations of base features.
        Captures complex patterns and interactions.
        """
        derived = {}
        
        # Extracting base values
        comments = issue.get('comments', 0)
        body = issue.get('body', '') or ''
        labels = issue.get('labels', [])
        language = issue.get('language', '')
        
        # Feature: Engagement ratio (comments per 100 chars of body)
        body_len = len(body)
        derived['engagement_ratio'] = comments / (body_len / 100 + 1)
        
        # Feature: Specification completeness
        has_body = 1 if body_len > 50 else 0
        has_labels = 1 if len(labels) > 0 else 0
        has_language = 1 if language else 0
        derived['spec_completeness'] = (has_body + has_labels + has_language) / 3
        
        # Feature: Issue maturity (based on comments and labels)
        derived['issue_maturity'] = min(5, comments // 3 + len(labels))
        
        # Feature: User-issue fit score
        lang_encoding = self.encode_language(language, user_languages)
        beginner_labels = ['good first issue', 'beginner', 'easy', 'starter']
        is_beginner = 1 if any(bl in [l.lower() for l in labels] for bl in beginner_labels) else 0
        
        derived['user_fit_score'] = (
            lang_encoding['language_proficiency'] * 0.5 +
            is_beginner * 3 +
            derived['spec_completeness'] * 2
        )
        
        # Feature: Estimated time to complete (heuristic)
        complexity_indicators = ['refactor', 'architecture', 'redesign', 'major']
        is_complex = any(ci in body.lower() or ci in ' '.join(labels).lower() for ci in complexity_indicators)
        derived['estimated_hours'] = 8 if is_complex else (4 if body_len > 500 else 2)
        
        return derived
    
    # =========================================
    # FULL FEATURE EXTRACTION
    # =========================================
    def extract_all_features(self, issue, user_languages):
        """
        Extracting complete feature set for single issue.
        Combines all feature types into unified vector.
        """
        features = {}
        
        # Text features from title
        title_features = self.extract_text_features(issue.get('title', ''))
        for k, v in title_features.items():
            features[f'title_{k}'] = v
        
        # Text features from body
        body_features = self.extract_text_features(issue.get('body', ''))
        for k, v in body_features.items():
            features[f'body_{k}'] = v
        
        # Label encoding
        label_features = self.encode_labels(issue.get('labels', []))
        features.update(label_features)
        
        # Language encoding
        lang_features = self.encode_language(issue.get('language', ''), user_languages)
        features.update(lang_features)
        
        # Derived features
        derived_features = self.create_derived_features(issue, user_languages)
        features.update(derived_features)
        
        # Raw numerical features
        features['comments'] = issue.get('comments', 0)
        features['repo_popularity'] = self._estimate_repo_popularity(issue.get('repo', ''))
        
        return features
    
    def _estimate_repo_popularity(self, repo_name):
        """
        Estimating repository popularity from name.
        Known popular repos get higher scores.
        """
        popular_orgs = ['facebook', 'google', 'microsoft', 'apache', 'tensorflow', 
                        'pytorch', 'kubernetes', 'docker', 'nodejs', 'vuejs', 'angular']
        
        repo_lower = repo_name.lower()
        for org in popular_orgs:
            if org in repo_lower:
                return 5
        return 3
    
    def extract_features_batch(self, issues, user_languages):
        """
        Extracting features for batch of issues.
        Returns list of feature vectors with statistics.
        """
        feature_vectors = []
        
        for issue in issues:
            features = self.extract_all_features(issue, user_languages)
            features['_issue_data'] = issue  # Preserving original data
            feature_vectors.append(features)
        
        # Calculating feature statistics
        if feature_vectors:
            numeric_keys = [k for k in feature_vectors[0].keys() 
                          if isinstance(feature_vectors[0][k], (int, float)) and not k.startswith('_')]
            
            self.feature_stats = {}
            for key in numeric_keys:
                values = [f[key] for f in feature_vectors]
                self.feature_stats[key] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'std': math.sqrt(sum((v - sum(values)/len(values))**2 for v in values) / len(values))
                }
        
        return feature_vectors, self.feature_stats


# Global feature engineer instance
feature_engineer = FeatureEngineer()

def get_feature_engineer():
    """Retrieving feature engineer instance."""
    return feature_engineer
