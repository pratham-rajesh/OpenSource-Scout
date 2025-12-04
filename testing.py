"""
Testing Module
==============
Implements model validation and evaluation:
- N-Fold Cross Validation
- Precision, Recall, F1 Score
- Hit Rate and NDCG metrics
- A/B Testing framework
"""

import random
import math
from collections import defaultdict


class ModelTester:
    """
    Model testing and validation framework.
    Implements cross-validation and recommendation metrics.
    """
    
    def __init__(self):
        self.test_results = []
        self.fold_metrics = []
    
    # =========================================
    # N-FOLD CROSS VALIDATION
    # =========================================
    def create_folds(self, data, n_folds=5, shuffle=True):
        """
        Splitting data into n folds for cross-validation.
        Returns list of (train, test) tuples.
        """
        if shuffle:
            data = data.copy()
            random.shuffle(data)
        
        fold_size = len(data) // n_folds
        folds = []
        
        for i in range(n_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < n_folds - 1 else len(data)
            
            test_set = data[start_idx:end_idx]
            train_set = data[:start_idx] + data[end_idx:]
            
            folds.append({
                'fold_num': i + 1,
                'train': train_set,
                'test': test_set,
                'train_size': len(train_set),
                'test_size': len(test_set)
            })
        
        return folds
    
    def run_cross_validation(self, data, model_func, n_folds=5):
        """
        Executing n-fold cross validation.
        Evaluates model performance across all folds.
        """
        folds = self.create_folds(data, n_folds)
        self.fold_metrics = []
        
        for fold in folds:
            # Training phase
            train_data = fold['train']
            test_data = fold['test']
            
            # Getting predictions from model
            predictions = model_func(train_data, test_data)
            
            # Evaluating fold performance
            fold_result = {
                'fold_num': fold['fold_num'],
                'train_size': fold['train_size'],
                'test_size': fold['test_size'],
                'predictions': len(predictions),
                'metrics': self.calculate_metrics(predictions, test_data)
            }
            
            self.fold_metrics.append(fold_result)
        
        # Aggregating results across folds
        aggregate = self._aggregate_fold_results()
        
        return {
            'n_folds': n_folds,
            'total_samples': len(data),
            'fold_results': self.fold_metrics,
            'aggregate_metrics': aggregate
        }
    
    def _aggregate_fold_results(self):
        """
        Aggregating metrics across all folds.
        Calculates mean and standard deviation.
        """
        if not self.fold_metrics:
            return {}
        
        metric_names = list(self.fold_metrics[0]['metrics'].keys())
        aggregate = {}
        
        for metric in metric_names:
            values = [f['metrics'][metric] for f in self.fold_metrics]
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_val = math.sqrt(variance)
            
            aggregate[metric] = {
                'mean': round(mean_val, 4),
                'std': round(std_val, 4),
                'min': round(min(values), 4),
                'max': round(max(values), 4)
            }
        
        return aggregate
    
    # =========================================
    # EVALUATION METRICS
    # =========================================
    def calculate_metrics(self, predictions, ground_truth):
        """
        Calculating recommendation evaluation metrics.
        Returns precision, recall, F1, and ranking metrics.
        """
        metrics = {}
        
        # Converting to sets for comparison
        pred_set = set(p.get('url', p.get('id', str(i))) for i, p in enumerate(predictions))
        truth_set = set(g.get('url', g.get('id', str(i))) for i, g in enumerate(ground_truth))
        
        # Calculating basic metrics
        true_positives = len(pred_set.intersection(truth_set))
        false_positives = len(pred_set - truth_set)
        false_negatives = len(truth_set - pred_set)
        
        # Precision: relevant items among recommended
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        
        # Recall: recommended items among relevant
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        # F1 Score: harmonic mean of precision and recall
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics['precision'] = round(precision, 4)
        metrics['recall'] = round(recall, 4)
        metrics['f1_score'] = round(f1, 4)
        
        # Hit Rate @ K
        metrics['hit_rate_5'] = self.calculate_hit_rate(predictions, ground_truth, k=5)
        metrics['hit_rate_10'] = self.calculate_hit_rate(predictions, ground_truth, k=10)
        
        # NDCG @ K
        metrics['ndcg_5'] = self.calculate_ndcg(predictions, ground_truth, k=5)
        metrics['ndcg_10'] = self.calculate_ndcg(predictions, ground_truth, k=10)
        
        # Coverage
        metrics['coverage'] = len(pred_set) / len(truth_set) if truth_set else 0
        
        return metrics
    
    def calculate_hit_rate(self, predictions, ground_truth, k=10):
        """
        Calculating Hit Rate @ K.
        Measures if relevant item appears in top-k recommendations.
        """
        top_k_preds = predictions[:k]
        pred_urls = set(p.get('url', '') for p in top_k_preds)
        truth_urls = set(g.get('url', '') for g in ground_truth)
        
        hits = len(pred_urls.intersection(truth_urls))
        hit_rate = hits / min(k, len(truth_urls)) if truth_urls else 0
        
        return round(hit_rate, 4)
    
    def calculate_ndcg(self, predictions, ground_truth, k=10):
        """
        Calculating Normalized Discounted Cumulative Gain @ K.
        Measures ranking quality with position-weighted relevance.
        """
        truth_urls = set(g.get('url', '') for g in ground_truth)
        
        # Calculating DCG
        dcg = 0
        for i, pred in enumerate(predictions[:k]):
            if pred.get('url', '') in truth_urls:
                relevance = 1
                dcg += relevance / math.log2(i + 2)  # i+2 because position starts at 1
        
        # Calculating ideal DCG
        ideal_dcg = sum(1 / math.log2(i + 2) for i in range(min(k, len(truth_urls))))
        
        # Normalizing
        ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0
        
        return round(ndcg, 4)
    
    def calculate_precision_at_k(self, predictions, ground_truth, k=10):
        """
        Calculating Precision @ K.
        Measures precision within top-k recommendations.
        """
        top_k = predictions[:k]
        pred_urls = set(p.get('url', '') for p in top_k)
        truth_urls = set(g.get('url', '') for g in ground_truth)
        
        relevant_in_top_k = len(pred_urls.intersection(truth_urls))
        precision_at_k = relevant_in_top_k / k if k > 0 else 0
        
        return round(precision_at_k, 4)
    
    # =========================================
    # A/B TESTING FRAMEWORK
    # =========================================
    def run_ab_test(self, data, model_a_func, model_b_func, test_size=0.3):
        """
        Running A/B test between two models.
        Compares performance on same test set.
        """
        # Splitting data
        random.shuffle(data)
        split_idx = int(len(data) * (1 - test_size))
        train_data = data[:split_idx]
        test_data = data[split_idx:]
        
        # Running Model A
        predictions_a = model_a_func(train_data, test_data)
        metrics_a = self.calculate_metrics(predictions_a, test_data)
        
        # Running Model B
        predictions_b = model_b_func(train_data, test_data)
        metrics_b = self.calculate_metrics(predictions_b, test_data)
        
        # Comparing results
        comparison = {}
        for metric in metrics_a.keys():
            diff = metrics_b[metric] - metrics_a[metric]
            improvement = (diff / metrics_a[metric] * 100) if metrics_a[metric] != 0 else 0
            comparison[metric] = {
                'model_a': metrics_a[metric],
                'model_b': metrics_b[metric],
                'difference': round(diff, 4),
                'improvement_pct': round(improvement, 2)
            }
        
        # Determining winner
        wins_a = sum(1 for m in comparison.values() if m['difference'] < 0)
        wins_b = sum(1 for m in comparison.values() if m['difference'] > 0)
        
        return {
            'test_size': len(test_data),
            'train_size': len(train_data),
            'model_a_metrics': metrics_a,
            'model_b_metrics': metrics_b,
            'comparison': comparison,
            'winner': 'Model A' if wins_a > wins_b else ('Model B' if wins_b > wins_a else 'Tie')
        }
    
    # =========================================
    # STATISTICAL SIGNIFICANCE
    # =========================================
    def calculate_confidence_interval(self, values, confidence=0.95):
        """
        Calculating confidence interval for metric values.
        Uses t-distribution approximation.
        """
        n = len(values)
        if n < 2:
            return {'mean': values[0] if values else 0, 'lower': 0, 'upper': 0}
        
        mean_val = sum(values) / n
        variance = sum((v - mean_val) ** 2 for v in values) / (n - 1)
        std_error = math.sqrt(variance / n)
        
        # t-value approximation for 95% confidence
        t_value = 2.0 if n > 30 else 2.5
        
        margin = t_value * std_error
        
        return {
            'mean': round(mean_val, 4),
            'lower': round(mean_val - margin, 4),
            'upper': round(mean_val + margin, 4),
            'std_error': round(std_error, 4)
        }
    
    # =========================================
    # GENERATING TEST REPORT
    # =========================================
    def generate_report(self, cv_results):
        """
        Generating comprehensive test report.
        Formats results for documentation.
        """
        report = []
        report.append("=" * 50)
        report.append("MODEL VALIDATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        report.append(f"Cross-Validation Folds: {cv_results['n_folds']}")
        report.append(f"Total Samples: {cv_results['total_samples']}")
        report.append("")
        
        # Aggregate Metrics
        report.append("-" * 50)
        report.append("AGGREGATE METRICS (Mean ± Std)")
        report.append("-" * 50)
        
        for metric, values in cv_results['aggregate_metrics'].items():
            report.append(f"{metric}: {values['mean']:.4f} ± {values['std']:.4f}")
        
        report.append("")
        
        # Per-Fold Results
        report.append("-" * 50)
        report.append("PER-FOLD RESULTS")
        report.append("-" * 50)
        
        for fold in cv_results['fold_results']:
            report.append(f"\nFold {fold['fold_num']}:")
            report.append(f"  Train size: {fold['train_size']}, Test size: {fold['test_size']}")
            for metric, value in fold['metrics'].items():
                report.append(f"  {metric}: {value:.4f}")
        
        report.append("")
        report.append("=" * 50)
        report.append("END OF REPORT")
        report.append("=" * 50)
        
        return "\n".join(report)


# Global tester instance
model_tester = ModelTester()

def get_model_tester():
    """Retrieving model tester instance."""
    return model_tester


# =========================================
# STANDALONE TEST FUNCTIONS
# =========================================
def run_recommendation_test(issues, user_languages, recommendation_func):
    """
    Running complete test suite for recommendation model.
    Returns validation results and performance metrics.
    """
    tester = get_model_tester()
    
    # Preparing test data
    test_data = [{'issue': issue, 'language': issue.get('language', '')} for issue in issues]
    
    # Defining model function wrapper
    def model_wrapper(train, test):
        train_issues = [t['issue'] for t in train]
        recommendations = recommendation_func(train_issues, user_languages)
        return recommendations
    
    # Running cross-validation
    cv_results = tester.run_cross_validation(test_data, model_wrapper, n_folds=5)
    
    # Generating report
    report = tester.generate_report(cv_results)
    
    return {
        'cv_results': cv_results,
        'report': report
    }
