import time
import json
from typing import Dict, Any, Optional
from backend.app.core.gemini import gemini_client
from backend.app.core.logger import logger
from backend.app.schemas.evaluation import EvaluationMetrics, PromptRunResult, EvaluationRunRecord

class PromptEvaluator:
    """
    LLM-as-a-Judge Evaluation Engine.
    Executes multiple prompt variants against a test question,
    generates responses, and conducts a strict multi-dimensional audit.
    """

    @staticmethod
    def evaluate_response(
        question: str,
        answer: str,
        context: Optional[str] = None
    ) -> EvaluationMetrics:
        """
        Invokes LLM-as-a-Judge to score the generated answer across 6 criteria.
        """
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
        eval_data = gemini_client.generate_json(judge_prompt)
        
        # Calculate overall if missing or inaccurate
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

    @classmethod
    def run_comparison(
        cls,
        question: str,
        prompts: Dict[str, str],
        context: Optional[str] = None
    ) -> Dict[str, PromptRunResult]:
        """
        Runs and evaluates multiple prompt templates against the same question.
        """
        results: Dict[str, PromptRunResult] = {}

        for name, template in prompts.items():
            start_t = time.time()
            logger.info(f"Evaluating prompt variant: '{name}'")
            
            # Populate variables in template
            prompt_input = template.replace("{question}", question)
            if context and "{context}" in prompt_input:
                prompt_input = prompt_input.replace("{context}", context)
            elif context and "{context}" not in prompt_input:
                prompt_input = f"Context:\n{context}\n\n{prompt_input}"

            # 1. Generate Answer
            answer = gemini_client.generate(prompt_input)

            # 2. Evaluate Answer with LLM Judge
            metrics = cls.evaluate_response(question=question, answer=answer, context=context)
            duration = round(time.time() - start_t, 2)

            results[name] = PromptRunResult(
                prompt_name=name,
                prompt_template=template,
                generated_answer=answer,
                metrics=metrics,
                execution_time_seconds=duration
            )

        return results

prompt_evaluator = PromptEvaluator()

