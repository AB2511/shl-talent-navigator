"""
System prompts and templates for LLM interactions.
Defines behavior for each state in the conversation flow.
"""
from app.schemas import Assessment


SYSTEM_PROMPT = """You are the SHL Talent Navigator, an expert assistant for recommending SHL assessments.

Your role is to help users find the most appropriate SHL assessments based on their needs.

STRICT RULES:
1. ONLY recommend assessments from the provided catalog - NEVER hallucinate or invent assessment names or URLs
2. ONLY discuss SHL assessments and talent assessment topics
3. Politely refuse off-topic requests (politics, personal advice, general knowledge, etc.)
4. Ask clarifying questions when requirements are vague
5. Provide 1-10 recommendations based on relevance
6. Use ONLY the URLs provided in the assessment catalog
7. Be concise, professional, and helpful

CONVERSATION STATES:
- insufficient_context: Need more information from user
- clarification: Ask specific questions to understand requirements
- recommendation: Provide relevant assessment recommendations
- refinement: Adjust recommendations based on new constraints
- comparison: Compare specific assessments side-by-side
- refusal: Politely decline off-topic requests

Always maintain context from conversation history to provide coherent responses."""


def get_clarification_prompt(user_query: str, conversation_history: str) -> str:
    """Generate prompt for clarification state."""
    return f"""The user has asked about SHL assessments but hasn't provided enough specific information.

User query: "{user_query}"

Conversation history:
{conversation_history}

Your task: Ask 2-3 specific clarifying questions to understand:
- What role or position are they hiring for?
- What skills or competencies are they looking to assess?
- What type of assessment are they interested in (cognitive, personality, behavioral, etc.)?
- Any constraints (time, candidate level, etc.)?

Be friendly and concise. Don't overwhelm with too many questions."""


def get_recommendation_prompt(
    user_query: str, 
    conversation_history: str, 
    retrieved_assessments: str
) -> str:
    """Generate prompt for recommendation state."""
    return f"""The user is looking for SHL assessment recommendations.

User query: "{user_query}"

Conversation history:
{conversation_history}

AVAILABLE ASSESSMENTS (from catalog):
{retrieved_assessments}

Your task: 
1. Recommend 1-10 most relevant assessments from the list above
2. Explain WHY each assessment is suitable for their needs
3. Mention key features (duration, skills measured, etc.)
4. Use ONLY the assessment names and URLs provided above
5. Order recommendations by relevance (most relevant first)

Be specific and helpful. Focus on matching their stated requirements."""


def get_refinement_prompt(
    user_query: str,
    conversation_history: str,
    previous_recommendations: str,
    retrieved_assessments: str
) -> str:
    """Generate prompt for refinement state."""
    return f"""The user wants to refine their assessment recommendations based on new constraints.

User query: "{user_query}"

Conversation history:
{conversation_history}

Previous recommendations:
{previous_recommendations}

AVAILABLE ASSESSMENTS (from catalog):
{retrieved_assessments}

Your task:
1. Understand what constraints or preferences have changed
2. Adjust recommendations accordingly
3. Explain what changed and why the new recommendations are better
4. Provide 1-10 refined recommendations from the available assessments
5. Use ONLY the assessment names and URLs provided

Be clear about how the recommendations have been adjusted."""


def get_comparison_prompt(
    user_query: str,
    conversation_history: str,
    assessments_to_compare: str
) -> str:
    """Generate prompt for comparison state."""
    return f"""The user wants to compare specific SHL assessments.

User query: "{user_query}"

Conversation history:
{conversation_history}

ASSESSMENTS TO COMPARE:
{assessments_to_compare}

Your task:
1. Create a clear comparison of the specified assessments
2. Compare: purpose, skills measured, duration, best use cases
3. Highlight key differences and similarities
4. Help the user understand which might be better for their specific needs
5. Use ONLY information from the assessments provided above

Be objective and informative. Use a structured format (table or bullet points)."""


def get_refusal_prompt(user_query: str, conversation_history: str) -> str:
    """Generate prompt for refusal state."""
    return f"""The user has asked about something outside your scope as an SHL assessment advisor.

User query: "{user_query}"

Conversation history:
{conversation_history}

Your task:
1. Politely explain that you can only help with SHL assessment recommendations
2. Briefly state what you CAN help with
3. Invite them to ask about SHL assessments

Be friendly but firm. Keep it brief (2-3 sentences)."""


def format_assessment_with_explanation(assessment: Assessment, query: str, constraints, confidence: int = None) -> str:
    """
    Format assessment with detailed explainability and confidence score.
    Shows WHY the assessment was recommended.
    Recruiter-oriented, concise tone.
    """
    reasons = []
    
    # Job level match
    if constraints.job_levels:
        matching_levels = set(assessment.job_levels) & set(constraints.job_levels)
        if matching_levels:
            reasons.append(f"Matches {', '.join(matching_levels)} level")
    
    # Remote testing
    if assessment.remote_testing:
        reasons.append("Remote testing available")
    
    # Duration
    if assessment.duration_minutes <= 30:
        reasons.append(f"Quick: {assessment.duration_minutes} mins")
    elif assessment.duration_minutes <= 60:
        reasons.append(f"Moderate: {assessment.duration_minutes} mins")
    
    # Test type explanation
    test_type_names = {
        "A": "Cognitive",
        "P": "Personality",
        "B": "Behavioral",
        "C": "Competency",
        "K": "Technical",
        "S": "Simulation"
    }
    test_types_explained = [test_type_names.get(t, t) for t in assessment.test_types]
    if test_types_explained:
        reasons.append(f"Type: {', '.join(test_types_explained)}")
    
    # Skills match (top 3)
    if constraints.skills:
        matching_skills = [s for s in assessment.skills if any(cs.lower() in s.lower() for cs in constraints.skills)]
        if matching_skills:
            reasons.append(f"Assesses: {', '.join(matching_skills[:3])}")
    elif assessment.skills:
        reasons.append(f"Assesses: {', '.join(assessment.skills[:3])}")
    
    # Format with confidence score
    confidence_str = f"**Match: {confidence}%**" if confidence else ""
    reason_bullets = "\n   • ".join(reasons) if reasons else "Relevant to requirements"
    
    return f"""**{assessment.name}** {confidence_str}
   • {reason_bullets}
   
   [View Details]({assessment.url})
"""


def format_assessments_for_prompt(assessments: list) -> str:
    """Format assessment list for inclusion in prompts."""
    if not assessments:
        return "No assessments available."
    
    formatted = []
    for i, assessment in enumerate(assessments, 1):
        formatted.append(
            f"{i}. {assessment.name} (ID: {assessment.id})\n"
            f"   Categories: {', '.join(assessment.categories)}\n"
            f"   Test Types: {', '.join(assessment.test_types)}\n"
            f"   Job Levels: {', '.join(assessment.job_levels)}\n"
            f"   Description: {assessment.description}\n"
            f"   Skills: {', '.join(assessment.skills)}\n"
            f"   Duration: {assessment.duration_minutes} minutes\n"
            f"   Remote Testing: {'Yes' if assessment.remote_testing else 'No'}\n"
            f"   URL: {assessment.url}\n"
        )
    
    return "\n".join(formatted)
