"""
Hybrid retrieval system combining semantic search, metadata filtering, and rule-based scoring.
This is the core improvement over basic embedding-only approaches.
"""
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

from app.schemas import Assessment
from app.constraints import ConversationConstraints


class HybridRetriever:
    """
    Advanced hybrid retrieval combining:
    1. Semantic similarity (embeddings)
    2. Hard metadata filtering
    3. Rule-based scoring/boosting
    4. Diversity enforcement
    """
    
    def __init__(self, assessments: List[Assessment]):
        """
        Initialize hybrid retriever.
        
        Args:
            assessments: Full assessment catalog
        """
        self.assessments = assessments
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Pre-compute embeddings for all assessments
        self.embeddings = self._compute_embeddings()
        
        # Build lookup index
        self.id_to_idx = {a.id: i for i, a in enumerate(assessments)}
    
    def _compute_embeddings(self) -> np.ndarray:
        """Compute embeddings for all assessments."""
        texts = []
        for assessment in self.assessments:
            # Combine all relevant text fields
            text = f"{assessment.name} {assessment.description} {' '.join(assessment.skills)} {' '.join(assessment.categories)}"
            texts.append(text)
        
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.astype('float32')
    
    def retrieve(
        self,
        query: str,
        constraints: ConversationConstraints,
        top_k: int = 10
    ) -> List[Assessment]:
        """
        Hybrid retrieval with semantic + metadata + rules.
        
        Args:
            query: User query text
            constraints: Accumulated conversation constraints
            top_k: Number of results to return
            
        Returns:
            Ranked list of assessments
        """
        # STEP 1: Hard filtering by metadata
        filtered = self._apply_hard_filters(constraints)
        
        if not filtered:
            # Fallback: relax some constraints
            filtered = self._apply_soft_filters(constraints)
        
        if not filtered:
            # Last resort: return all
            filtered = self.assessments.copy()
        
        # STEP 2: Semantic similarity scoring
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        scored_assessments = []
        for assessment in filtered:
            idx = self.id_to_idx[assessment.id]
            
            # Semantic similarity score (cosine similarity)
            semantic_score = float(np.dot(query_embedding, self.embeddings[idx]))
            
            # STEP 3: Rule-based boosting
            boost_score = self._compute_boost(assessment, constraints, query)
            
            # Combined score
            final_score = semantic_score + boost_score
            
            scored_assessments.append((assessment, final_score))
        
        # Sort by score
        scored_assessments.sort(key=lambda x: x[1], reverse=True)
        
        # STEP 4: Diversity enforcement
        diverse_results = self._enforce_diversity(scored_assessments, top_k)
        
        return diverse_results[:top_k]
    
    def _apply_hard_filters(self, constraints: ConversationConstraints) -> List[Assessment]:
        """
        Apply STRICT metadata filters.
        These are HARD CONSTRAINTS that FILTER OUT assessments, not just rank them.
        """
        filtered = self.assessments.copy()
        
        # HARD CONSTRAINT: Duration (MUST satisfy, not just prefer)
        if constraints.max_duration is not None:
            filtered = [a for a in filtered if a.duration_minutes <= constraints.max_duration]
        
        if constraints.min_duration is not None:
            filtered = [a for a in filtered if a.duration_minutes >= constraints.min_duration]
        
        # HARD CONSTRAINT: Remote testing (MUST have if required)
        if constraints.remote_testing is True:
            filtered = [a for a in filtered if a.remote_testing]
        
        # HARD CONSTRAINT: Adaptive (MUST have if required)
        if constraints.adaptive_required is True:
            filtered = [a for a in filtered if a.adaptive_irt]
        
        # SOFT CONSTRAINT: Job level (prefer match, but don't filter out)
        # This allows flexibility while still prioritizing matches
        if constraints.job_levels:
            # Don't filter - let ranking handle this
            pass
        
        # SOFT CONSTRAINT: Test type (prefer match, but don't filter out)
        if constraints.test_types:
            # Don't filter - let ranking handle this
            pass
        
        # HARD CONSTRAINT: Language (MUST support if specified)
        if constraints.languages:
            filtered = [
                a for a in filtered
                if any(lang in a.languages for lang in constraints.languages)
            ]
        
        # HARD CONSTRAINT: Exclusions (MUST NOT include)
        if constraints.exclude_ids:
            filtered = [a for a in filtered if a.id not in constraints.exclude_ids]
        
        return filtered
    
    def _apply_soft_filters(self, constraints: ConversationConstraints) -> List[Assessment]:
        """Apply relaxed filters (only critical ones)."""
        filtered = self.assessments.copy()
        
        # Only apply duration and exclusions
        if constraints.max_duration is not None:
            filtered = [a for a in filtered if a.duration_minutes <= constraints.max_duration * 1.5]
        
        if constraints.exclude_ids:
            filtered = [a for a in filtered if a.id not in constraints.exclude_ids]
        
        return filtered
    
    def _compute_boost(
        self,
        assessment: Assessment,
        constraints: ConversationConstraints,
        query: str
    ) -> float:
        """
        Compute rule-based boost score with ROLE-SPECIFIC BOOSTING.
        
        Scoring weights (tuned for sharper ranking):
        - Role-specific match: +0.40 (INCREASED - highest priority)
        - Job level match: +0.25
        - Skill overlap: +0.20
        - Test type match: +0.15
        - Duration match: +0.10
        - Query keyword density: +0.10
        """
        boost = 0.0
        query_lower = query.lower()
        assessment_text = f"{assessment.name} {assessment.description} {' '.join(assessment.skills)}".lower()
        
        # ROLE-SPECIFIC BOOSTING (highest priority)
        # This dramatically improves precision by heavily weighting role matches
        role_specific_patterns = {
            "software_engineer": {
                "query_keywords": ["software", "developer", "engineer", "programming", "coding", "technical", "swe"],
                "assessment_keywords": ["software", "engineer", "programming", "coding", "technical", "developer"],
                "boost": 0.40
            },
            "sales": {
                "query_keywords": ["sales", "selling", "revenue", "business development", "account"],
                "assessment_keywords": ["sales", "selling", "revenue", "commercial"],
                "boost": 0.40
            },
            "customer_service": {
                "query_keywords": ["customer", "service", "support", "client", "helpdesk"],
                "assessment_keywords": ["customer", "service", "support", "contact"],
                "boost": 0.40
            },
            "leadership": {
                "query_keywords": ["leadership", "leader", "management", "manager", "executive"],
                "assessment_keywords": ["leadership", "leader", "management", "managerial"],
                "boost": 0.40
            },
            "finance": {
                "query_keywords": ["finance", "accounting", "financial", "analyst", "cpa"],
                "assessment_keywords": ["finance", "accounting", "financial", "numerical"],
                "boost": 0.40
            },
            "graduate": {
                "query_keywords": ["graduate", "entry", "junior", "trainee", "new grad"],
                "assessment_keywords": ["graduate", "entry"],
                "boost": 0.30  # Lower boost for general graduate
            }
        }
        
        # Check for role-specific matches
        role_matched = False
        for role, patterns in role_specific_patterns.items():
            query_has_role = any(kw in query_lower for kw in patterns["query_keywords"])
            assessment_has_role = any(kw in assessment_text for kw in patterns["assessment_keywords"])
            
            if query_has_role and assessment_has_role:
                boost += patterns["boost"]
                role_matched = True
                break
        
        # Penalize generic assessments when specific role is mentioned
        if not role_matched:
            # Check if query is role-specific but assessment is generic
            is_role_specific_query = any(
                any(kw in query_lower for kw in patterns["query_keywords"])
                for patterns in role_specific_patterns.values()
            )
            
            is_generic_assessment = "battery" in assessment_text or "general" in assessment_text
            
            if is_role_specific_query and is_generic_assessment:
                boost -= 0.15  # Penalize generic assessments for specific queries
        
        # Job level match (strong weight)
        if constraints.job_levels:
            if any(level in assessment.job_levels for level in constraints.job_levels):
                boost += 0.25
        
        # Skill overlap (granular matching)
        if constraints.skills:
            assessment_skills_lower = [s.lower() for s in assessment.skills]
            constraint_skills_lower = [s.lower() for s in constraints.skills]
            
            # Exact matches
            exact_matches = len(set(assessment_skills_lower) & set(constraint_skills_lower))
            
            # Partial matches (substring)
            partial_matches = sum(
                1 for cs in constraint_skills_lower
                if any(cs in as_skill for as_skill in assessment_skills_lower)
            )
            
            if exact_matches > 0:
                boost += 0.20 * (exact_matches / len(constraint_skills_lower))
            elif partial_matches > 0:
                boost += 0.10 * (partial_matches / len(constraint_skills_lower))
        
        # Test type match
        if constraints.test_types:
            matching_types = set(assessment.test_types) & set(constraints.test_types)
            if matching_types:
                boost += 0.15 * (len(matching_types) / len(constraints.test_types))
        
        # Duration match (prefer closer to constraint)
        if constraints.max_duration:
            if assessment.duration_minutes <= constraints.max_duration:
                # Closer to max is better (but not too short)
                ratio = assessment.duration_minutes / constraints.max_duration
                if ratio >= 0.5:  # Penalize very short assessments
                    boost += 0.10 * ratio
        
        # Query keyword density
        query_keywords = set(query_lower.split()) - {
            'the', 'a', 'an', 'for', 'to', 'of', 'in', 'and', 'or', 'i', 'need', 'want', 'looking'
        }
        if query_keywords:
            keyword_matches = sum(1 for kw in query_keywords if kw in assessment_text)
            keyword_density = keyword_matches / len(query_keywords)
            boost += 0.10 * keyword_density
        
        return boost
    
    def _enforce_diversity(
        self,
        scored_assessments: List[Tuple[Assessment, float]],
        top_k: int
    ) -> List[Assessment]:
        """
        Enforce diversity in results to avoid repetitive recommendations.
        
        Strategy: Ensure mix of test types and categories.
        """
        if len(scored_assessments) <= top_k:
            return [a for a, _ in scored_assessments]
        
        selected = []
        seen_test_types = set()
        seen_categories = set()
        
        # First pass: select diverse items
        for assessment, score in scored_assessments:
            if len(selected) >= top_k:
                break
            
            # Check diversity
            test_type_key = tuple(sorted(assessment.test_types))
            category_key = tuple(sorted(assessment.categories))
            
            # Prefer unseen combinations
            if test_type_key not in seen_test_types or category_key not in seen_categories:
                selected.append(assessment)
                seen_test_types.add(test_type_key)
                seen_categories.add(category_key)
        
        # Second pass: fill remaining slots with highest scores
        if len(selected) < top_k:
            for assessment, score in scored_assessments:
                if len(selected) >= top_k:
                    break
                if assessment not in selected:
                    selected.append(assessment)
        
        return selected
    
    def get_by_ids(self, assessment_ids: List[str]) -> List[Assessment]:
        """Retrieve specific assessments by IDs."""
        return [
            self.assessments[self.id_to_idx[aid]]
            for aid in assessment_ids
            if aid in self.id_to_idx
        ]
