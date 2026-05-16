"""
API route handlers for FastAPI application.
Implements /health and /chat endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from app.schemas import ChatRequest, ChatResponse, Message, Assessment
from app.state_machine import StateMachine
from app.hybrid_retrieval import HybridRetriever
from app.llm import LLMClient
from app.catalog_loader import CatalogLoader
from app.constraints import ConstraintExtractor
from app import prompts


router = APIRouter()

# Global instances (initialized in main.py)
catalog_loader: CatalogLoader = None
hybrid_retriever: HybridRetriever = None
state_machine: StateMachine = None
llm_client: LLMClient = None
constraint_extractor: ConstraintExtractor = None


def get_conversation_history(messages: List[Message]) -> str:
    """Format conversation history for prompts."""
    history = []
    for msg in messages[:-1]:  # Exclude latest message
        history.append(f"{msg.role.upper()}: {msg.content}")
    return "\n".join(history)


def extract_assessment_ids_from_history(messages: List[Message]) -> List[str]:
    """Extract assessment IDs mentioned in conversation history."""
    # Simplified extraction - in production, use more sophisticated NER
    assessment_ids = []
    
    for msg in messages:
        if msg.role == "assistant":
            # Look for assessment IDs in format (ID: xxx)
            import re
            ids = re.findall(r'\(ID: ([\w-]+)\)', msg.content)
            assessment_ids.extend(ids)
    
    return list(set(assessment_ids))  # Remove duplicates


def _calculate_confidence_score(assessment: Assessment, query: str, constraints) -> int:
    """
    Calculate confidence score (0-100) for recommendation.
    Heuristic-based scoring for perceived intelligence.
    """
    score = 50  # Base score
    
    query_lower = query.lower()
    
    # Job level match (+20)
    if constraints.job_levels:
        matching_levels = set(assessment.job_levels) & set(constraints.job_levels)
        if matching_levels:
            score += 20
    
    # Skills match (+15)
    if constraints.skills:
        matching_skills = sum(1 for s in assessment.skills if any(cs.lower() in s.lower() for cs in constraints.skills))
        score += min(matching_skills * 5, 15)
    
    # Query keyword match (+10)
    query_keywords = set(query_lower.split()) - {'the', 'a', 'an', 'for', 'to', 'of', 'in', 'and', 'or'}
    assessment_text = f"{assessment.name} {assessment.description} {' '.join(assessment.skills)}".lower()
    keyword_matches = sum(1 for kw in query_keywords if kw in assessment_text)
    score += min(keyword_matches * 2, 10)
    
    # Duration match (+5)
    if constraints.max_duration and assessment.duration_minutes <= constraints.max_duration:
        score += 5
    
    # Remote testing match (+5)
    if constraints.remote_testing and assessment.remote_testing:
        score += 5
    
    # Test type match (+5)
    if constraints.test_types:
        if any(tt in assessment.test_types for tt in constraints.test_types):
            score += 5
    
    return min(score, 99)  # Cap at 99


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint for conversational assessment recommendations.
    
    Stateless design: reconstructs conversation state from message history.
    Uses hybrid retrieval with constraint accumulation.
    """
    try:
        # STEP 1: Extract cumulative constraints from full conversation
        constraints = constraint_extractor.extract_from_messages(request.messages)
        
        # STEP 2: Determine conversation state
        state = state_machine.determine_state(request.messages)
        
        # Get latest user message
        latest_message = request.messages[-1].content
        conversation_history = get_conversation_history(request.messages)
        
        # STEP 3: Handle different states
        if state == "refusal":
            # DETERMINISTIC: No LLM call for refusal
            response_text = state_machine.get_deterministic_refusal_response()
            return ChatResponse(
                response=response_text,
                state=state,
                assessments=[]
            )
        
        elif state == "clarification":
            # DETERMINISTIC: No LLM call for clarification
            response_text = state_machine.get_deterministic_clarification_questions(constraints)
            return ChatResponse(
                response=response_text,
                state=state,
                assessments=[]
            )
        
        elif state == "recommendation":
            response_text, assessments = await _handle_recommendation(
                latest_message,
                conversation_history,
                constraints
            )
            return ChatResponse(
                response=response_text,
                state=state,
                assessments=assessments
            )
        
        elif state == "refinement":
            response_text, assessments = await _handle_refinement(
                latest_message,
                conversation_history,
                request.messages,
                constraints
            )
            return ChatResponse(
                response=response_text,
                state=state,
                assessments=assessments
            )
        
        elif state == "comparison":
            response_text, assessments = await _handle_comparison(
                latest_message,
                conversation_history,
                request.messages
            )
            return ChatResponse(
                response=response_text,
                state=state,
                assessments=assessments
            )
        
        else:  # insufficient_context
            # DETERMINISTIC: No LLM call for clarification
            response_text = state_machine.get_deterministic_clarification_questions(constraints)
            return ChatResponse(
                response=response_text,
                state="clarification",
                assessments=[]
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


async def _handle_refusal(query: str, history: str) -> str:
    """Handle off-topic requests with polite refusal."""
    prompt = prompts.get_refusal_prompt(query, history)
    response = await llm_client.generate(
        prompt=prompt,
        system_prompt=prompts.SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=200
    )
    return response


async def _handle_clarification(query: str, history: str, constraints) -> str:
    """Handle clarification requests with intelligent question ordering."""
    # Build context about what we already know
    known_info = []
    if constraints.job_levels:
        known_info.append(f"Job level: {', '.join(constraints.job_levels)}")
    if constraints.role:
        known_info.append(f"Role: {constraints.role}")
    if constraints.skills:
        known_info.append(f"Skills: {', '.join(constraints.skills)}")
    
    context = f"Known information: {'; '.join(known_info)}" if known_info else "No specific information yet"
    
    prompt = f"""{prompts.get_clarification_prompt(query, history)}

{context}

Focus your questions on what's still missing (prioritize: role, level, skills, duration)."""
    
    response = await llm_client.generate(
        prompt=prompt,
        system_prompt=prompts.SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=300
    )
    return response


async def _handle_recommendation(
    query: str,
    history: str,
    constraints
) -> tuple[str, List[Assessment]]:
    """Handle assessment recommendations using hybrid retrieval with explainability."""
    # Use hybrid retrieval with accumulated constraints
    retrieved = hybrid_retriever.retrieve(
        query=query,
        constraints=constraints,
        top_k=10  # Retrieve 10 for diversity, show top 3
    )
    
    if not retrieved:
        return "I couldn't find any assessments matching your criteria. Could you provide more details or relax some constraints?", []
    
    # Limit to top 3 for better UX (cognitive load optimization)
    top_recommendations = retrieved[:3]
    
    # Generate recommendation response with explainability
    if llm_client and not llm_client.template_mode:
        # Use LLM for natural language response
        assessments_text = prompts.format_assessments_for_prompt(top_recommendations)
        constraint_summary = f"User constraints: {constraints.to_dict()}" if not constraints.is_empty() else ""
        
        prompt = f"""{prompts.get_recommendation_prompt(query, history, assessments_text)}

{constraint_summary}

IMPORTANT: 
- Recommend ONLY the top 3 most relevant assessments
- For each, explain WHY it matches using the assessment metadata
- Keep explanations concise and recruiter-oriented
- Add match confidence scores"""
        
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=prompts.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=600
        )
    else:
        # Use template response with explainability and confidence scores
        response = "**Top matches for your requirements:**\n\n"
        for i, assessment in enumerate(top_recommendations, 1):
            # Calculate simple confidence score
            confidence = _calculate_confidence_score(assessment, query, constraints)
            response += f"{i}. {prompts.format_assessment_with_explanation(assessment, query, constraints, confidence)}\n"
        
        if len(retrieved) > 3:
            response += f"\n💡 *Showing top 3 of {len(retrieved)} matches. Need more options? Ask to see alternatives.*"
    
    return response, top_recommendations


async def _handle_refinement(
    query: str,
    history: str,
    messages: List[Message],
    constraints
) -> tuple[str, List[Assessment]]:
    """Handle refinement of previous recommendations with cumulative constraints and explainability."""
    # Get previous recommendations from history
    previous_ids = extract_assessment_ids_from_history(messages)
    
    # Use hybrid retrieval with updated constraints
    retrieved = hybrid_retriever.retrieve(
        query=query,
        constraints=constraints,
        top_k=10
    )
    
    if not retrieved:
        return "I couldn't find assessments matching your refined criteria. Could you adjust your requirements?", []
    
    # Generate refinement response
    if llm_client and not llm_client.template_mode:
        # Get previous recommendations for context
        previous_assessments = catalog_loader.get_assessments_by_ids(previous_ids[:5])
        previous_text = prompts.format_assessments_for_prompt(previous_assessments)
        assessments_text = prompts.format_assessments_for_prompt(retrieved)
        constraint_summary = f"Updated constraints: {constraints.to_dict()}"
        
        prompt = f"""{prompts.get_refinement_prompt(query, history, previous_text, assessments_text)}

{constraint_summary}

IMPORTANT: Explain what changed and WHY the new recommendations better match their updated requirements."""
        
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=prompts.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=800
        )
    else:
        # Use template response with explainability
        response = "I've refined the recommendations based on your updated requirements:\n\n"
        for i, assessment in enumerate(retrieved[:5], 1):
            response += f"{i}. {prompts.format_assessment_with_explanation(assessment, query, constraints)}\n"
        
        response += "\nThese assessments better match your refined criteria."
    
    return response, retrieved


async def _handle_comparison(
    query: str,
    history: str,
    messages: List[Message]
) -> tuple[str, List[Assessment]]:
    """Handle comparison of specific assessments with structured table output."""
    # Extract assessment IDs from history
    assessment_ids = extract_assessment_ids_from_history(messages)
    
    if not assessment_ids:
        return "I don't see any specific assessments to compare. Could you mention which assessments you'd like to compare?", []
    
    # Get assessments for comparison (limit to 5)
    assessments = catalog_loader.get_assessments_by_ids(assessment_ids[:5])
    
    if len(assessments) < 2:
        return "I need at least two assessments to compare. Could you specify which assessments you're interested in?", []
    
    # Generate structured comparison table
    if llm_client and not llm_client.template_mode:
        assessments_text = prompts.format_assessments_for_prompt(assessments)
        
        prompt = f"""{prompts.get_comparison_prompt(query, history, assessments_text)}

Create a structured comparison table in markdown format covering:
- Duration
- Job Levels
- Test Types
- Key Skills
- Remote Testing
- Best Use Cases"""
        
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=prompts.SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=1000
        )
    else:
        # Use structured table comparison
        response = "**Assessment Comparison**\n\n"
        response += "| Assessment | Duration | Job Levels | Type | Remote | Key Skills |\n"
        response += "|------------|----------|------------|------|--------|------------|\n"
        
        for assessment in assessments:
            name = assessment.name[:30] + "..." if len(assessment.name) > 30 else assessment.name
            duration = f"{assessment.duration_minutes}m"
            levels = ", ".join(assessment.job_levels[:2])
            types = ", ".join(assessment.test_types)
            remote = "✓" if assessment.remote_testing else "✗"
            skills = ", ".join(assessment.skills[:2])
            
            response += f"| {name} | {duration} | {levels} | {types} | {remote} | {skills} |\n"
        
        response += "\n**Key Differences:**\n"
        
        # Duration comparison
        durations = [a.duration_minutes for a in assessments]
        shortest = min(durations)
        longest = max(durations)
        response += f"• Duration range: {shortest}-{longest} minutes\n"
        
        # Remote testing
        remote_count = sum(1 for a in assessments if a.remote_testing)
        response += f"• Remote testing: {remote_count}/{len(assessments)} assessments\n"
        
        # Test types
        all_types = set()
        for a in assessments:
            all_types.update(a.test_types)
        response += f"• Test types covered: {', '.join(sorted(all_types))}\n"
    
    return response, assessments
