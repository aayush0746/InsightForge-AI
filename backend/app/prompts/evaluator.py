import time
from typing import Dict, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.evaluation import EvaluationMetrics, PromptRunResult


class PromptEvaluator:
    """
    LLM-as-a-Judge Evaluation Engine with deterministic structural rubric fallback
    when GEMINI_API_KEY is not configured.
    """

    @staticmethod
    def _local_generate(question: str, template: str, context: Optional[str] = None) -> str:
        t_lower = template.lower()
        persona = "Structured Expert Response" if ("expert" in t_lower or "architect" in t_lower or "consultant" in t_lower) else "Direct Response"
        has_rules = "rules:" in t_lower or "- " in template
        has_steps = "step" in t_lower or "roadmap" in t_lower or "prioritize" in t_lower

        sections = [f"[{persona} — Local Simulation Mode (set GEMINI_API_KEY for live Gemini output)]"]
        sections.append(f"Question Addressed: {question}")
        if context:
            sections.append(f"Grounded Context Excerpt: {context[:400]}")
        if has_steps or has_rules:
            sections.append(
                "1. Core Foundations: Master essential programming, data structures, and ML/RAG retrieval principles first.\n"
                "2. Applied Architecture: Implement hybrid dense+BM25 retrieval, reranking, and strict evaluation rubrics.\n"
                "3. Verification & Next Step: Benchmark outputs systematically with clear guardrails before deployment."
            )
        else:
            sections.append(f"Summary answer for '{question}': Focus on core concepts, practical implementation, and continuous evaluation.")
        return "\n\n".join(sections)

    @staticmethod
    def _local_evaluate(question: str, template: str, answer: str, context: Optional[str] = None) -> EvaluationMetrics:
        t_lower = template.lower()
        has_role = any(k in t_lower for k in ["you are", "expert", "architect", "consultant", "analyst"])
        has_rules = any(k in t_lower for k in ["rules:", "- ", "1.", "must", "avoid"])
        has_structure = any(k in t_lower for k in ["roadmap", "step", "prioritize", "distinguish", "conclude"])
        has_grounding = any(k in t_lower for k in ["only", "cite", "context", "not assume", "not available"])

        rel = round(min(9.5, 6.2 + (1.2 if "{question}" in template else 0.0) + (0.8 if has_role else 0.0) + (0.6 if has_rules else 0.0)), 1)
        acc = round(min(9.5, 6.5 + (1.2 if has_grounding else 0.4) + (0.8 if has_rules else 0.0)), 1)
        cla = round(min(9.6, 5.8 + (1.5 if has_structure else 0.2) + (1.2 if has_rules else 0.0)), 1)
        comp = round(min(9.5, 5.5 + (1.4 if len(template) > 160 else 0.2) + (1.2 if has_structure else 0.0) + (0.7 if has_role else 0.0)), 1)
        act = round(min(9.5, 5.6 + (1.6 if has_steps_or_action(t_lower) else 0.2) + (1.0 if has_rules else 0.0)), 1)
        fai = round(min(9.8, 6.5 + (2.0 if has_grounding else 0.5) + (0.5 if context else 0.3)), 1)
        overall = round((rel + acc + cla + comp + act + fai) / 6.0, 1)

        strengths = []
        if has_role:
            strengths.append("explicit persona framing")
        if has_rules:
            strengths.append("clear constraint rules")
        if has_structure:
            strengths.append("structured progression")
        if not strengths:
            strengths.append("concise direct framing")

        weakness = "Lacks explicit citation/grounding constraints" if not has_grounding else "Relies on local heuristic rubric while GEMINI_API_KEY is unset"
        feedback = (
            f"Local Heuristic Evaluation (configure GEMINI_API_KEY for live LLM-as-a-Judge): "
            f"Strongest part: {', '.join(strengths)}. Biggest weakness: {weakness}. "
            f"Concrete improvement: Add explicit output formatting and grounding constraints."
        )
        return EvaluationMetrics(
            relevance=rel,
            accuracy=acc,
            clarity=cla,
            completeness=comp,
            actionability=act,
            faithfulness=fai,
            overall=overall,
            feedback=feedback
        )

    @staticmethod
    def evaluate_response(
        question: str,
        answer: str,
        context: Optional[str] = None,
        template: str = ""
    ) -> EvaluationMetrics:
        if not gemini_client.is_configured:
            return PromptEvaluator._local_evaluate(question, template, answer, context)

        judge_prompt = f"""
You are a strict, unbiased AI Evaluation Judge.
Evaluate the following AI-generated answer for the provided question.

CRITICAL RULES:
- Be strict. Do NOT award high scores automatically.
- Evaluate each criterion independently from 1 to 10.
- A score of 10 represents exceptional, professional publication-grade excellence.

QUESTION:
{question}

{"CONTEXT PROVIDED:" + chr(10) + context if context else "No extra context provided."}

ANSWER UNDER EVALUATION:
{answer}

CRITERIA:
1. RELEVANCE (1-10): Does the answer directly address the question without irrelevant tangents?
2. ACCURACY (1-10): Are the factual and technical claims correct and sound?
3. CLARITY (1-10): Is the structure, formatting, and prose easy to comprehend?
4. COMPLETENESS (1-10): Does it cover all vital facets of the user question?
5. ACTIONABILITY (1-10): Can the user readily execute the recommendations or steps provided?
6. FAITHFULNESS (1-10): Does the response avoid hallucinations and stay faithful to known facts / context?

FEEDBACK:
Provide concise feedback stating:
1. The strongest part.
2. The biggest weakness.
3. One concrete improvement.

Return ONLY valid JSON matching this schema:
{{
    "relevance": 8.0,
    "accuracy": 8.5,
    "clarity": 9.0,
    "completeness": 7.5,
    "actionability": 8.0,
    "faithfulness": 9.0,
    "overall": 8.3,
    "feedback": "Strongest part... Biggest weakness... Concrete improvement..."
}}
"""
        try:
            eval_data = gemini_client.generate_json(judge_prompt)
            r = float(eval_data.get("relevance", 7.0))
            ac = float(eval_data.get("accuracy", 7.0))
            cl = float(eval_data.get("clarity", 7.0))
            co = float(eval_data.get("completeness", 7.0))
            act = float(eval_data.get("actionability", 7.0))
            fai = float(eval_data.get("faithfulness", 7.0))
            avg = round((r + ac + cl + co + act + fai) / 6.0, 1)

            return EvaluationMetrics(
                relevance=r,
                accuracy=ac,
                clarity=cl,
                completeness=co,
                actionability=act,
                faithfulness=fai,
                overall=float(eval_data.get("overall", avg)),
                feedback=str(eval_data.get("feedback", "No feedback provided."))
            )
        except Exception as e:
            logger.warning(f"Gemini judge failed ({e}); using local rubric evaluation.")
            return PromptEvaluator._local_evaluate(question, template, answer, context)

    @classmethod
    def run_comparison(
        cls,
        question: str,
        prompts: Dict[str, str],
        context: Optional[str] = None
    ) -> Dict[str, PromptRunResult]:
        results: Dict[str, PromptRunResult] = {}

        for name, template in prompts.items():
            start_t = time.time()
            logger.info(f"Evaluating prompt variant: '{name}'")

            prompt_input = template.replace("{question}", question)
            if context and "{context}" in prompt_input:
                prompt_input = prompt_input.replace("{context}", context)
            elif context and "{context}" not in prompt_input:
                prompt_input = f"Context:\n{context}\n\n{prompt_input}"

            if gemini_client.is_configured:
                try:
                    answer = gemini_client.generate(prompt_input)
                except Exception as e:
                    logger.warning(f"Gemini generation failed for '{name}' ({e}); using local simulation.")
                    answer = cls._local_generate(question, template, context)
            else:
                answer = cls._local_generate(question, template, context)

            metrics = cls.evaluate_response(question=question, answer=answer, context=context, template=template)
            duration = round(time.time() - start_t, 2)

            results[name] = PromptRunResult(
                prompt_name=name,
                prompt_template=template,
                generated_answer=answer,
                metrics=metrics,
                execution_time_seconds=duration
            )

        return results


def has_steps_or_action(text: str) -> bool:
    return any(k in text for k in ["actionable", "step", "practical", "roadmap", "recommend"])


prompt_evaluator = PromptEvaluator()
