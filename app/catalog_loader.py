"""
SHL Assessment Catalog Loader.
Manages the assessment catalog with metadata for retrieval and recommendations.
"""
from typing import List, Dict
from app.schemas import Assessment
from app.catalog_expanded import load_expanded_catalog


class CatalogLoader:
    """Loads and manages the SHL assessment catalog."""
    
    def __init__(self):
        """Initialize catalog with SHL assessments."""
        self._catalog: List[Assessment] = self._load_catalog()
        self._catalog_dict: Dict[str, Assessment] = {
            assessment.id: assessment for assessment in self._catalog
        }
    
    def _load_catalog(self) -> List[Assessment]:
        """
        Load SHL assessment catalog with full structured metadata.
        Uses expanded catalog with 37 assessments.
        """
        return load_expanded_catalog()

    
    def get_all_assessments(self) -> List[Assessment]:
        """Return all assessments in catalog."""
        return self._catalog.copy()
    
    def get_assessment_by_id(self, assessment_id: str) -> Assessment | None:
        """Retrieve specific assessment by ID."""
        return self._catalog_dict.get(assessment_id)
    
    def get_assessments_by_ids(self, assessment_ids: List[str]) -> List[Assessment]:
        """Retrieve multiple assessments by IDs."""
        return [
            self._catalog_dict[aid] 
            for aid in assessment_ids 
            if aid in self._catalog_dict
        ]
    
    def get_catalog_size(self) -> int:
        """Return number of assessments in catalog."""
        return len(self._catalog)
    
    def search_by_category(self, category: str) -> List[Assessment]:
        """Filter assessments by category."""
        return [
            a for a in self._catalog 
            if any(category.lower() in c.lower() for c in a.categories)
        ]
    
    def search_by_skill(self, skill: str) -> List[Assessment]:
        """Filter assessments by skill."""
        skill_lower = skill.lower()
        return [
            a for a in self._catalog 
            if any(skill_lower in s.lower() for s in a.skills)
        ]
    
    def search_by_test_type(self, test_type: str) -> List[Assessment]:
        """Filter assessments by test type (A, P, B, C, S, K)."""
        return [
            a for a in self._catalog
            if test_type.upper() in a.test_types
        ]
    
    def search_by_job_level(self, job_level: str) -> List[Assessment]:
        """Filter assessments by job level."""
        return [
            a for a in self._catalog
            if job_level in a.job_levels
        ]
