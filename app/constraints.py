"""
Constraint accumulation and management.
Maintains conversation-level constraints across multiple turns.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.schemas import Message


class ConversationConstraints(BaseModel):
    """Accumulated constraints from conversation history."""
    
    # Role and level
    role: Optional[str] = None
    job_levels: List[str] = []
    
    # Skills and competencies
    skills: List[str] = []
    
    # Technical requirements
    max_duration: Optional[int] = None
    min_duration: Optional[int] = None
    remote_testing: Optional[bool] = None
    adaptive_required: Optional[bool] = None
    languages: List[str] = []
    
    # Test preferences
    test_types: List[str] = []  # A, P, B, C, S, K
    categories: List[str] = []
    
    # Exclusions
    exclude_ids: List[str] = []
    
    def merge(self, other: "ConversationConstraints") -> "ConversationConstraints":
        """Merge with new constraints, keeping non-None values."""
        merged = self.copy(deep=True)
        
        if other.role:
            merged.role = other.role
        if other.job_levels:
            merged.job_levels = list(set(merged.job_levels + other.job_levels))
        if other.skills:
            merged.skills = list(set(merged.skills + other.skills))
        if other.max_duration is not None:
            merged.max_duration = other.max_duration
        if other.min_duration is not None:
            merged.min_duration = other.min_duration
        if other.remote_testing is not None:
            merged.remote_testing = other.remote_testing
        if other.adaptive_required is not None:
            merged.adaptive_required = other.adaptive_required
        if other.languages:
            merged.languages = list(set(merged.languages + other.languages))
        if other.test_types:
            merged.test_types = list(set(merged.test_types + other.test_types))
        if other.categories:
            merged.categories = list(set(merged.categories + other.categories))
        if other.exclude_ids:
            merged.exclude_ids = list(set(merged.exclude_ids + other.exclude_ids))
        
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return self.dict(exclude_none=True, exclude_defaults=True)
    
    def is_empty(self) -> bool:
        """Check if any constraints are set."""
        d = self.to_dict()
        return len(d) == 0


class ConstraintExtractor:
    """Extract and accumulate constraints from conversation."""
    
    # Test type mappings (Complete SHL Classification)
    TEST_TYPE_KEYWORDS = {
        "A": ["ability", "cognitive", "aptitude", "reasoning", "intelligence", "iq", "numerical", "verbal"],
        "B": ["biodata", "situational", "judgment", "situational judgement", "sjt"],
        "C": ["competency", "competencies", "skills assessment", "competence"],
        "D": ["development", "360", "360 feedback", "development center", "feedback"],
        "E": ["assessment exercise", "exercise", "in-tray", "group exercise"],
        "K": ["knowledge", "technical knowledge", "coding", "programming", "technical skills"],
        "P": ["personality", "traits", "behavioral traits", "character", "opq", "behavior"],
        "S": ["simulation", "assessment center", "role play", "virtual assessment"]
    }
    
    # Job level mappings
    JOB_LEVEL_KEYWORDS = {
        "Graduate": ["graduate", "grad", "entry-level", "junior", "fresh", "new grad"],
        "Entry": ["entry", "entry-level", "junior", "beginner"],
        "Mid-Professional": ["mid", "mid-level", "professional", "experienced", "intermediate"],
        "Manager": ["manager", "management", "supervisor", "team lead", "lead"],
        "Senior": ["senior", "senior-level", "advanced", "expert"],
        "Executive": ["executive", "c-level", "director", "vp", "chief", "head of"]
    }
    
    # Role keywords for common positions
    ROLE_KEYWORDS = {
        "sales": ["sales", "account manager", "business development"],
        "customer_service": ["customer service", "support", "client success"],
        "technical": ["developer", "engineer", "programmer", "software", "technical"],
        "leadership": ["leader", "manager", "director", "executive"],
        "administrative": ["admin", "administrative", "coordinator", "assistant"]
    }
    
    def extract_from_messages(self, messages: List[Message]) -> ConversationConstraints:
        """
        Extract cumulative constraints from entire conversation history.
        
        Args:
            messages: Full conversation history
            
        Returns:
            Accumulated constraints
        """
        constraints = ConversationConstraints()
        
        # Process all user messages to accumulate constraints
        for msg in messages:
            if msg.role == "user":
                msg_constraints = self._extract_from_text(msg.content)
                constraints = constraints.merge(msg_constraints)
        
        return constraints
    
    def _extract_from_text(self, text: str) -> ConversationConstraints:
        """Extract constraints from a single text message."""
        text_lower = text.lower()
        constraints = ConversationConstraints()
        
        # Extract job levels
        for level, keywords in self.JOB_LEVEL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                constraints.job_levels.append(level)
        
        # Extract test types
        for test_type, keywords in self.TEST_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                constraints.test_types.append(test_type)
        
        # Extract role
        for role_type, keywords in self.ROLE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                constraints.role = role_type
                break
        
        # Extract duration constraints
        import re
        
        # "under X minutes", "less than X min", "maximum X min"
        duration_patterns = [
            (r'under (\d+)\s*min', 'max'),
            (r'less than (\d+)\s*min', 'max'),
            (r'maximum (\d+)\s*min', 'max'),
            (r'max (\d+)\s*min', 'max'),
            (r'at least (\d+)\s*min', 'min'),
            (r'minimum (\d+)\s*min', 'min'),
            (r'(\d+)\s*minutes? or less', 'max'),
        ]
        
        for pattern, constraint_type in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                duration = int(match.group(1))
                if constraint_type == 'max':
                    constraints.max_duration = duration
                else:
                    constraints.min_duration = duration
                break
        
        # Quick/short keywords
        if any(word in text_lower for word in ["quick", "short", "brief", "fast"]):
            if not constraints.max_duration:
                constraints.max_duration = 20
        
        # Remote testing
        if any(word in text_lower for word in ["remote", "online", "virtual", "distance"]):
            constraints.remote_testing = True
        
        # Adaptive
        if any(word in text_lower for word in ["adaptive", "irt", "computer adaptive"]):
            constraints.adaptive_required = True
        
        # Extract skills (common ones)
        skill_keywords = [
            "leadership", "management", "communication", "teamwork", "analytical",
            "numerical", "verbal", "problem-solving", "critical thinking",
            "customer service", "sales", "technical", "coding", "programming"
        ]
        
        for skill in skill_keywords:
            if skill in text_lower:
                constraints.skills.append(skill)
        
        return constraints
    
    def extract_exclusions(self, messages: List[Message]) -> List[str]:
        """Extract assessment IDs that user wants to exclude."""
        exclusions = []
        
        for msg in messages:
            if msg.role == "user":
                text_lower = msg.content.lower()
                if any(word in text_lower for word in ["not", "exclude", "without", "except", "different"]):
                    # Extract IDs from previous messages
                    import re
                    ids = re.findall(r'\(ID:\s*([\w-]+)\)', msg.content)
                    exclusions.extend(ids)
        
        return list(set(exclusions))
