from typing import List, Dict
from backend.app.schemas.evaluation import PromptTemplate

DEFAULT_PROMPT_TEMPLATES: List[PromptTemplate] = [
    PromptTemplate(
        id="tmpl_basic",
        name="Basic Prompt",
        category="General",
        description="Direct question asking without role definition or formatting constraints.",
        template="{question}"
    ),
    PromptTemplate(
        id="tmpl_role_based",
        name="Role-Based Consultant Prompt",
        category="Consulting",
        description="Assigns a senior industry expert persona with practical guidance guidelines.",
        template="""You are an experienced GenAI career consultant and senior AI engineer.
Answer the following question:
{question}

Provide practical, realistic, and highly actionable recommendations.
Avoid jargon where simpler terms suffice."""
    ),
    PromptTemplate(
        id="tmpl_advanced_cot",
        name="Advanced Strategic Roadmap (CoT)",
        category="Strategy",
        description="Comprehensive structured prompt with clear scope boundaries, rules, and breakdown.",
        template="""You are an expert GenAI Architect and Lead Research Advisor.
Analyze the following user question thoroughly:

{question}

Provide an actionable, comprehensive, and well-structured response.
Rules:
- Prioritize the most critical and impactful concepts first.
- Provide concrete, step-by-step guidance.
- Distinguish essential foundational knowledge from optional advanced topics.
- Keep each recommendation concise and grounded.
- Avoid repetitive or vague advice.
- Conclude with a recommended next step."""
    ),
    PromptTemplate(
        id="tmpl_grounded_rag",
        name="Grounded Document Analyst",
        category="RAG",
        description="Strictly bounds answers to context with explicit refusal for missing data.",
        template="""You are InsightForge AI, an analytical document research assistant.
Answer the question below using ONLY the provided document context.

Context:
{context}

Question:
{question}

Rules:
- Do not assume or extrapolate beyond the stated text.
- If information is missing, state: "Information not available in the document."
- Cite page numbers and section references."""
    )
]

def get_default_templates() -> List[PromptTemplate]:
    return DEFAULT_PROMPT_TEMPLATES

