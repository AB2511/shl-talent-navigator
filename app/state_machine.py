"""
Deterministic state machine for conversation flow management.
Analyzes conversation history to determine current state and next action.
"""
from typing import List, Tuple, Literal
import re

from app.schemas import Message


ConversationState = Literal[
    "insufficient_context",
    "clarification", 
    "recommendation",
    "refinement",
    "comparison",
    "refusal"
]


class StateMachine:
    """Lightweight deterministic state machine for conversation management."""
    
    # Explicit state transition table
    TRANSITIONS = {
        "insufficient_context": ["clarification", "recommendation", "refusal"],
        "clarification": ["recommendation", "refusal"],
        "recommendation": ["refinement", "comparison", "clarification"],
        "refinement": ["recommendation", "comparison"],
        "comparison": ["recommendation", "refinement"],
        "refusal": []  # Terminal state
    }
    
    # Keywords indicating off-topic requests
    OFF_TOPIC_KEYWORDS = [
        "weather", "news", "politics", "recipe", "joke", "story",
        "movie", "game", "sports", "celebrity", "music", "travel",
        "health advice", "medical", "legal advice", "financial advice",
        "election", "president", "government", "religion", "dating"
    ]
    
    # Keywords indicating assessment-related queries
    ASSESSMENT_KEYWORDS = [
        "assessment", "test", "evaluation", "screening", "shl",
        "cognitive", "personality", "aptitude", "skill", "talent",
        "hire", "recruit", "candidate", "employee", "leadership",
        "verify", "opq", "questionnaire"
    ]
    
    # Keywords indicating comparison requests
    COMPARISON_KEYWORDS = [
        "compare", "comparison", "difference", "versus", "vs",
        "better", "which one", "choose between", "contrast"
    ]
    
    # Keywords indicating refinement requests
    REFINEMENT_KEYWORDS = [
        "shorter", "longer", "faster", "different", "instead",
        "other", "alternative", "more specific", "less", "exclude",
        "without", "narrow down", "refine", "adjust"
    ]
    
    def __init__(self):
        """Initialize state machine."""
        pass
    
    def determine_state(self, messages: List[Message]) -> ConversationState:
        """
        Determine conversation state from message history.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Current conversation state
        """
        if not messages:
            return "insufficient_context"
        
        # Get latest user message
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return "insufficient_context"
        
        latest_user_msg = user_messages[-1].content.lower()
        
        # Check for off-topic requests
        if self._is_off_topic(latest_user_msg):
            return "refusal"
        
        # Check for comparison requests
        if self._is_comparison_request(latest_user_msg, messages):
            return "comparison"
        
        # Check for refinement requests
        if self._is_refinement_request(messages):
            return "refinement"
        
        # Check if we have enough context for recommendations
        if self._has_sufficient_context(latest_user_msg):
            return "recommendation"
        
        # Check if we're already in clarification phase
        if self._is_in_clarification(messages):
            # If user provided more info, try recommendation
            if len(user_messages) > 1:
                return "recommendation"
            return "clarification"
        
        # Default: need clarification
        return "clarification"
    
    def _is_off_topic(self, message: str) -> bool:
        """Check if message is off-topic (not about assessments)."""
        message_lower = message.lower()
        
        # Check for off-topic keywords
        if any(keyword in message_lower for keyword in self.OFF_TOPIC_KEYWORDS):
            # But allow if also mentions assessments
            if not any(keyword in message_lower for keyword in self.ASSESSMENT_KEYWORDS):
                return True
        
        # Check if message is too short and vague
        if len(message.split()) < 3 and not any(
            keyword in message_lower for keyword in self.ASSESSMENT_KEYWORDS
        ):
            return False  # Too vague, not necessarily off-topic
        
        # If message is long but doesn't mention assessments at all
        if len(message.split()) > 10 and not any(
            keyword in message_lower for keyword in self.ASSESSMENT_KEYWORDS
        ):
            return True
        
        return False
    
    def _is_comparison_request(self, message: str, messages: List[Message]) -> bool:
        """Check if user is requesting comparison of assessments."""
        message_lower = message.lower()
        
        # Check for comparison keywords
        has_comparison_keyword = any(
            keyword in message_lower for keyword in self.COMPARISON_KEYWORDS
        )
        
        # Check if previous recommendations exist
        has_previous_recommendations = len(messages) > 2
        
        return has_comparison_keyword and has_previous_recommendations
    
    def _is_refinement_request(self, messages: List[Message]) -> bool:
        """Check if user is refining previous recommendations."""
        if len(messages) < 3:  # Need at least user -> assistant -> user
            return False
        
        # Check if there was a previous recommendation
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if not assistant_messages:
            return False
        
        # Check latest user message for refinement keywords
        user_messages = [m for m in messages if m.role == "user"]
        if len(user_messages) < 2:
            return False
        
        latest_user_msg = user_messages[-1].content.lower()
        
        return any(
            keyword in latest_user_msg for keyword in self.REFINEMENT_KEYWORDS
        )
    
    def _has_sufficient_context(self, message: str) -> bool:
        """Check if message has enough context for recommendations."""
        message_lower = message.lower()
        
        # Check for assessment-related keywords
        has_assessment_keyword = any(
            keyword in message_lower for keyword in self.ASSESSMENT_KEYWORDS
        )
        
        # Check for specific requirements (role, skill, etc.)
        has_specific_requirement = any([
            re.search(r'\b(role|position|job)\b', message_lower),
            re.search(r'\b(skill|ability|competenc)', message_lower),
            re.search(r'\b(cognitive|personality|behavioral|technical)\b', message_lower),
            re.search(r'\b(leadership|management|sales|customer)\b', message_lower),
            len(message.split()) > 8  # Longer messages likely have more context
        ])
        
        return has_assessment_keyword and has_specific_requirement
    
    def _is_in_clarification(self, messages: List[Message]) -> bool:
        """Check if conversation is in clarification phase."""
        if len(messages) < 2:
            return False
        
        # Check if last assistant message was asking questions
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if not assistant_messages:
            return False
        
        last_assistant_msg = assistant_messages[-1].content.lower()
        
        # Look for question marks indicating clarification
        question_count = last_assistant_msg.count("?")
        
        return question_count >= 2  # Multiple questions = clarification
    
    def get_deterministic_refusal_response(self) -> str:
        """
        Return static refusal response without LLM call.
        DETERMINISTIC: No LLM required for off-topic queries.
        """
        return """I'm the SHL Talent Navigator, specialized in helping you find the right SHL assessments for your hiring and talent development needs.

I can only assist with questions about SHL assessments, talent evaluation, and hiring recommendations.

How can I help you find the right assessment for your needs?"""
    
    def get_deterministic_clarification_questions(self, constraints) -> str:
        """
        Return deterministic clarification questions based on missing information.
        ADAPTIVE: Asks most informative missing field first.
        DETERMINISTIC: No LLM required for clarification.
        
        Priority order (most informative first):
        1. Role (highest impact on relevance)
        2. Job level (strong filtering power)
        3. Test type (narrows scope significantly)
        4. Duration (hard constraint)
        5. Skills (refinement)
        """
        questions = []
        
        # Priority 1: Role (most informative)
        if not constraints.role and not constraints.skills:
            questions.append("What role or position are you hiring for?")
            # Stop here - role is most informative, get it first
            if len(questions) >= 1:
                intro = "To recommend the most suitable assessments, I need one key detail:\n\n"
                return intro + "• " + questions[0]
        
        # Priority 2: Job level (strong filtering)
        if not constraints.job_levels:
            questions.append("What job level are you targeting? (e.g., Graduate, Professional, Manager, Executive)")
            if len(questions) >= 1:
                intro = "To narrow down the best options:\n\n"
                return intro + "• " + questions[0]
        
        # Priority 3: Test type (scope narrowing)
        if not constraints.test_types:
            questions.append("What type of assessment? (Cognitive ability, Personality, Behavioral, Technical skills)")
            if len(questions) >= 1:
                intro = "To refine recommendations:\n\n"
                return intro + "• " + questions[0]
        
        # Priority 4: Duration (hard constraint)
        if constraints.max_duration is None:
            questions.append("Do you have a time limit? (e.g., under 30 minutes, under 60 minutes)")
            if len(questions) >= 1:
                intro = "One more detail would help:\n\n"
                return intro + "• " + questions[0]
        
        # Priority 5: Skills (refinement)
        if not constraints.skills and constraints.role:
            questions.append("What specific skills or competencies do you want to assess?")
            if len(questions) >= 1:
                intro = "To fine-tune recommendations:\n\n"
                return intro + "• " + questions[0]
        
        # Default: ask for any additional requirements
        if not questions:
            return "I have enough information to recommend assessments. Would you like to add any specific requirements? (e.g., remote testing, specific skills, duration limits)"
        
        # Fallback (shouldn't reach here)
        intro = "To recommend the most suitable assessments:\n\n"
        return intro + "• " + questions[0]
    
    def validate_transition(self, from_state: ConversationState, to_state: ConversationState) -> bool:
        """
        Validate if state transition is allowed.
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if transition is valid
        """
        return to_state in self.TRANSITIONS.get(from_state, [])
    
    def extract_comparison_targets(self, messages: List[Message]) -> List[str]:
        """
        Extract assessment names/IDs mentioned for comparison.
        
        Args:
            messages: Conversation history
            
        Returns:
            List of assessment identifiers mentioned
        """
        # Get latest user message
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return []
        
        latest_msg = user_messages[-1].content
        
        # Extract potential assessment names (simplified)
        # In production, this would use NER or more sophisticated extraction
        assessment_patterns = [
            r'verify[- ]?g\+?',
            r'opq',
            r'verify[- ]?numerical',
            r'verify[- ]?verbal',
            r'verify[- ]?inductive',
            r'motivation questionnaire',
            r'situational judgement',
            r'leadership report',
            r'graduate battery',
            r'mechanical comprehension',
            r'checking test',
            r'work styles',
        ]
        
        mentioned = []
        latest_lower = latest_msg.lower()
        
        for pattern in assessment_patterns:
            if re.search(pattern, latest_lower):
                mentioned.append(pattern)
        
        return mentioned[:5]  # Limit to 5 comparisons
