"""
Assessment filtering logic.
Extracts filters from user queries and conversation context.
"""
import re
from typing import List, Optional, Tuple


class FilterExtractor:
    """Extract filtering criteria from user queries."""
    
    # Category mappings
    CATEGORY_KEYWORDS = {
        "cognitive": ["cognitive", "reasoning", "aptitude", "intelligence", "problem-solving"],
        "personality": ["personality", "behavioral traits", "work style", "character"],
        "behavioral": ["behavioral", "situational", "judgment", "decision-making"],
        "leadership": ["leadership", "management", "executive", "leader"],
        "motivation": ["motivation", "engagement", "drive", "motivators"],
        "technical": ["technical", "mechanical", "engineering", "technical skills"]
    }
    
    # Skill keywords
    SKILL_KEYWORDS = [
        "leadership", "teamwork", "communication", "analytical", "numerical",
        "verbal", "problem-solving", "critical thinking", "attention to detail",
        "customer service", "sales", "management", "planning", "organization"
    ]
    
    def extract_filters(self, query: str, conversation_history: str = "") -> Tuple[
        Optional[str],  # category
        Optional[List[str]],  # skills
        Optional[int]  # max_duration
    ]:
        """
        Extract filtering criteria from query.
        
        Args:
            query: User query text
            conversation_history: Previous conversation context
            
        Returns:
            Tuple of (category, skills, max_duration)
        """
        query_lower = query.lower()
        combined_text = f"{conversation_history} {query}".lower()
        
        # Extract category
        category = self._extract_category(combined_text)
        
        # Extract skills
        skills = self._extract_skills(combined_text)
        
        # Extract duration constraint
        max_duration = self._extract_duration(query_lower)
        
        return category, skills, max_duration
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract assessment category from text."""
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return category
        return None
    
    def _extract_skills(self, text: str) -> Optional[List[str]]:
        """Extract skill requirements from text."""
        found_skills = []
        
        for skill in self.SKILL_KEYWORDS:
            if skill in text:
                found_skills.append(skill)
        
        return found_skills if found_skills else None
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract maximum duration constraint from text."""
        # Look for patterns like "under 30 minutes", "less than 20 min", "quick", "short"
        
        # Quick/short keywords
        if any(word in text for word in ["quick", "short", "brief", "fast"]):
            return 20  # Assume 20 minutes for quick assessments
        
        # Explicit duration mentions
        duration_patterns = [
            r'under (\d+) min',
            r'less than (\d+) min',
            r'maximum (\d+) min',
            r'max (\d+) min',
            r'(\d+) minutes? or less',
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        
        return None
    
    def extract_role_context(self, text: str) -> Optional[str]:
        """Extract role/position context from text."""
        # Common role patterns
        role_patterns = [
            r'for (?:a |an )?(\w+(?:\s+\w+){0,2}) (?:role|position|job)',
            r'hiring (?:a |an )?(\w+(?:\s+\w+){0,2})',
            r'(\w+(?:\s+\w+){0,2}) candidate',
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        
        return None
    
    def is_vague_query(self, query: str) -> bool:
        """Check if query is too vague and needs clarification."""
        query_lower = query.lower().strip()
        
        # Very short queries
        if len(query_lower.split()) < 4:
            return True
        
        # Generic phrases without specifics
        vague_phrases = [
            "need assessment",
            "looking for test",
            "want to assess",
            "help me find",
            "what assessment",
            "which test"
        ]
        
        if any(phrase in query_lower for phrase in vague_phrases):
            # Check if there are specific details
            has_specifics = any([
                self._extract_category(query_lower),
                self._extract_skills(query_lower),
                self.extract_role_context(query_lower)
            ])
            return not has_specifics
        
        return False
