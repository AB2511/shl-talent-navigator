"""
Retrieval-Augmented Generation (RAG) using FAISS vector store.
Handles embedding generation and similarity search for assessment recommendations.
"""
import os
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from app.catalog_loader import CatalogLoader
from app.schemas import Assessment


class VectorRetriever:
    """FAISS-based vector retrieval for assessment recommendations."""
    
    def __init__(self, catalog_loader: CatalogLoader):
        """
        Initialize retriever with catalog and embedding model.
        
        Args:
            catalog_loader: CatalogLoader instance with assessment catalog
        """
        self.catalog_loader = catalog_loader
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        self.assessment_ids: List[str] = []
        
        # Build index
        self._build_index()
    
    def _build_index(self) -> None:
        """Build FAISS index from assessment catalog."""
        assessments = self.catalog_loader.get_all_assessments()
        
        # Create searchable text for each assessment
        texts = []
        for assessment in assessments:
            # Combine all relevant fields for better retrieval
            text = f"{assessment.name} {assessment.description} {assessment.category} {' '.join(assessment.skills)}"
            texts.append(text)
            self.assessment_ids.append(assessment.id)
        
        # Generate embeddings
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = 10,
        filter_category: str | None = None,
        filter_skills: List[str] | None = None
    ) -> List[Assessment]:
        """
        Retrieve most relevant assessments for a query.
        
        Args:
            query: User query text
            top_k: Number of results to return (max 10)
            filter_category: Optional category filter
            filter_skills: Optional skills filter
            
        Returns:
            List of Assessment objects ranked by relevance
        """
        # Limit to max 10 recommendations
        top_k = min(top_k, 10)
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # Search FAISS index (retrieve more for filtering)
        search_k = min(top_k * 3, len(self.assessment_ids))
        distances, indices = self.index.search(query_embedding.astype('float32'), search_k)
        
        # Retrieve assessments
        retrieved_ids = [self.assessment_ids[idx] for idx in indices[0]]
        assessments = self.catalog_loader.get_assessments_by_ids(retrieved_ids)
        
        # Apply filters
        filtered_assessments = self._apply_filters(
            assessments, 
            filter_category, 
            filter_skills
        )
        
        # Return top_k results
        return filtered_assessments[:top_k]
    
    def _apply_filters(
        self,
        assessments: List[Assessment],
        filter_category: str | None,
        filter_skills: List[str] | None
    ) -> List[Assessment]:
        """
        Apply category and skill filters to assessments.
        
        Args:
            assessments: List of assessments to filter
            filter_category: Category filter
            filter_skills: Skills filter
            
        Returns:
            Filtered list of assessments
        """
        filtered = assessments
        
        # Category filter
        if filter_category:
            filtered = [
                a for a in filtered 
                if a.category.lower() == filter_category.lower()
            ]
        
        # Skills filter (assessment must have at least one matching skill)
        if filter_skills:
            skills_lower = [s.lower() for s in filter_skills]
            filtered = [
                a for a in filtered
                if any(
                    any(skill_lower in a_skill.lower() for a_skill in a.skills)
                    for skill_lower in skills_lower
                )
            ]
        
        return filtered
    
    def get_assessments_by_ids(self, assessment_ids: List[str]) -> List[Assessment]:
        """Retrieve specific assessments by IDs for comparison."""
        return self.catalog_loader.get_assessments_by_ids(assessment_ids)
    
    def is_loaded(self) -> bool:
        """Check if vector store is properly loaded."""
        return self.index.ntotal > 0
