"""
Evaluation metrics for retrieval quality assessment.

IMPORTANT: These are INTERNAL evaluation metrics for engineering purposes.
NOT academic benchmarks or scientifically rigorous measurements.

Limitations:
- Small test set (3 cases)
- Handpicked relevance labels
- Heuristic scoring
- No human evaluation
- No cross-validation

Use for:
- Internal quality tracking
- Retrieval engineering
- Regression testing
- Demo purposes

Do NOT claim:
- State-of-the-art performance
- Academic benchmark results
- Production-validated metrics
"""
from typing import List, Set, Dict
from app.schemas import Assessment
from app.constraints import ConversationConstraints


class RetrievalMetrics:
    """
    Internal evaluation metrics for hybrid retrieval system.
    
    NOTE: These metrics are for internal engineering use, not academic benchmarking.
    """
    
    @staticmethod
    def precision_at_k(
        retrieved: List[Assessment],
        relevant_ids: Set[str],
        k: int = 3
    ) -> float:
        """
        Calculate Precision@K.
        
        Args:
            retrieved: List of retrieved assessments
            relevant_ids: Set of IDs considered relevant
            k: Number of top results to consider
            
        Returns:
            Precision score (0.0 to 1.0)
        """
        if not retrieved or k == 0:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for a in top_k if a.id in relevant_ids)
        
        return relevant_in_top_k / k
    
    @staticmethod
    def recall_at_k(
        retrieved: List[Assessment],
        relevant_ids: Set[str],
        k: int = 10
    ) -> float:
        """
        Calculate Recall@K.
        
        Args:
            retrieved: List of retrieved assessments
            relevant_ids: Set of IDs considered relevant
            k: Number of top results to consider
            
        Returns:
            Recall score (0.0 to 1.0)
        """
        if not relevant_ids:
            return 0.0
        
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for a in top_k if a.id in relevant_ids)
        
        return relevant_in_top_k / len(relevant_ids)
    
    @staticmethod
    def mean_reciprocal_rank(
        retrieved: List[Assessment],
        relevant_ids: Set[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR).
        
        Args:
            retrieved: List of retrieved assessments
            relevant_ids: Set of IDs considered relevant
            
        Returns:
            MRR score (0.0 to 1.0)
        """
        for i, assessment in enumerate(retrieved, 1):
            if assessment.id in relevant_ids:
                return 1.0 / i
        
        return 0.0
    
    @staticmethod
    def constraint_satisfaction_score(
        retrieved: List[Assessment],
        constraints: ConversationConstraints
    ) -> float:
        """
        Calculate constraint satisfaction score.
        Measures how well retrieved assessments match constraints.
        
        Args:
            retrieved: List of retrieved assessments
            constraints: Conversation constraints
            
        Returns:
            Satisfaction score (0.0 to 1.0)
        """
        if not retrieved:
            return 0.0
        
        total_score = 0.0
        num_constraints = 0
        
        for assessment in retrieved:
            assessment_score = 0.0
            assessment_constraints = 0
            
            # Job level constraint
            if constraints.job_levels:
                assessment_constraints += 1
                if any(level in assessment.job_levels for level in constraints.job_levels):
                    assessment_score += 1.0
            
            # Duration constraint
            if constraints.max_duration is not None:
                assessment_constraints += 1
                if assessment.duration_minutes <= constraints.max_duration:
                    assessment_score += 1.0
            
            if constraints.min_duration is not None:
                assessment_constraints += 1
                if assessment.duration_minutes >= constraints.min_duration:
                    assessment_score += 1.0
            
            # Remote testing constraint
            if constraints.remote_testing is not None:
                assessment_constraints += 1
                if assessment.remote_testing == constraints.remote_testing:
                    assessment_score += 1.0
            
            # Adaptive constraint
            if constraints.adaptive_required is not None:
                assessment_constraints += 1
                if assessment.adaptive_irt == constraints.adaptive_required:
                    assessment_score += 1.0
            
            # Test type constraint
            if constraints.test_types:
                assessment_constraints += 1
                if any(tt in assessment.test_types for tt in constraints.test_types):
                    assessment_score += 1.0
            
            # Skills constraint
            if constraints.skills:
                assessment_constraints += 1
                assessment_skills_lower = [s.lower() for s in assessment.skills]
                constraint_skills_lower = [s.lower() for s in constraints.skills]
                overlap = len(set(assessment_skills_lower) & set(constraint_skills_lower))
                if overlap > 0:
                    assessment_score += overlap / len(constraint_skills_lower)
            
            if assessment_constraints > 0:
                total_score += assessment_score / assessment_constraints
                num_constraints += 1
        
        return total_score / len(retrieved) if retrieved else 0.0
    
    @staticmethod
    def diversity_score(retrieved: List[Assessment]) -> float:
        """
        Calculate diversity score based on test types and categories.
        
        Args:
            retrieved: List of retrieved assessments
            
        Returns:
            Diversity score (0.0 to 1.0)
        """
        if not retrieved:
            return 0.0
        
        # Count unique test types
        unique_test_types = set()
        for assessment in retrieved:
            unique_test_types.update(assessment.test_types)
        
        # Count unique categories
        unique_categories = set()
        for assessment in retrieved:
            unique_categories.update(assessment.categories)
        
        # Diversity is ratio of unique types/categories to total assessments
        test_type_diversity = len(unique_test_types) / len(retrieved)
        category_diversity = len(unique_categories) / len(retrieved)
        
        return (test_type_diversity + category_diversity) / 2
    
    @staticmethod
    def evaluate_retrieval(
        retrieved: List[Assessment],
        relevant_ids: Set[str],
        constraints: ConversationConstraints,
        k: int = 3
    ) -> Dict[str, float]:
        """
        Comprehensive retrieval evaluation.
        
        Args:
            retrieved: List of retrieved assessments
            relevant_ids: Set of IDs considered relevant
            constraints: Conversation constraints
            k: Number of top results for precision/recall
            
        Returns:
            Dictionary of metric scores
        """
        metrics = RetrievalMetrics()
        
        return {
            "precision@3": metrics.precision_at_k(retrieved, relevant_ids, k=3),
            "precision@5": metrics.precision_at_k(retrieved, relevant_ids, k=5),
            "recall@10": metrics.recall_at_k(retrieved, relevant_ids, k=10),
            "mrr": metrics.mean_reciprocal_rank(retrieved, relevant_ids),
            "constraint_satisfaction": metrics.constraint_satisfaction_score(retrieved, constraints),
            "diversity": metrics.diversity_score(retrieved)
        }


# Test cases for evaluation
EVALUATION_TEST_CASES = [
    {
        "query": "cognitive assessment for graduate software engineers",
        "constraints": {
            "job_levels": ["Graduate"],
            "skills": ["problem-solving", "logical reasoning"]
        },
        "relevant_ids": {
            "shl-verify-g-plus",
            "shl-software-engineer",
            "shl-verify-inductive",
            "shl-verify-numerical"
        }
    },
    {
        "query": "quick personality test for sales roles",
        "constraints": {
            "max_duration": 30,
            "test_types": ["P"]
        },
        "relevant_ids": {
            "shl-opq",
            "shl-motivation-questionnaire",
            "shl-work-styles"
        }
    },
    {
        "query": "leadership assessment for managers",
        "constraints": {
            "job_levels": ["Manager", "Senior"],
            "skills": ["leadership", "decision-making"]
        },
        "relevant_ids": {
            "shl-leadership-report",
            "shl-managerial-assessment",
            "shl-situational-judgement"
        }
    }
]
