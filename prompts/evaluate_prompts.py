
import os
import json
from dotenv import load_dotenv
from google import genai

# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

# ============================================================
# 2. CREATE GEMINI CLIENT
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(
    api_key=api_key
)

# ============================================================
# 3. QUESTION WE WANT TO TEST
# ============================================================

question = """
How can a final-year computer science student prepare for a GenAI job?
"""

# ============================================================
# 4. DIFFERENT PROMPT STRATEGIES
# ============================================================

prompts = {

    "Basic Prompt": f"""
{question}
""",

   "Advanced Prompt": f"""
You are an expert GenAI career consultant helping a
final-year computer science student prepare for a GenAI job.

Analyze the following question:

{question}

Create a practical and comprehensive roadmap.

Cover these areas:

1. Computer Science and programming fundamentals
2. Machine Learning and Deep Learning fundamentals
3. Generative AI and LLM concepts
4. Prompt Engineering
5. RAG and Vector Databases
6. AI Agents and Tool Calling
7. LLM Evaluation and Guardrails
8. Projects and Portfolio
9. Deployment and MLOps
10. Technical Interview Preparation
11. A realistic learning timeline

Rules:
- Prioritize the most important skills.
- Give actionable recommendations.
- Explain why important skills matter.
- Avoid unnecessary repetition.
- Keep recommendations realistic for a final-year student.
- Do not assume advanced industry experience.
- Distinguish essential skills from optional advanced topics.
- Organize the answer in a logical progression.
- Keep the answer focused and practical.
"""
}

# ============================================================
# 5. FUNCTION TO GENERATE AN ANSWER
# ============================================================

def generate_answer(prompt):

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    return response.output_text


# ============================================================
# 6. FUNCTION TO EVALUATE AN ANSWER
# ============================================================

def evaluate_answer(question, answer):

    evaluation_prompt = f"""
You are a strict and unbiased AI response evaluator.

Your job is to evaluate the quality of an AI-generated answer.

Do NOT automatically give high scores.

You must identify both strengths AND weaknesses before assigning scores.

============================================================
USER QUESTION
============================================================

{question}

============================================================
ANSWER TO EVALUATE
============================================================

{answer}

============================================================
EVALUATION CRITERIA
============================================================

Evaluate these five criteria independently.

============================================================
1. RELEVANCE
============================================================

Does the answer directly address the user's question?

Scoring:

1-2 = Mostly unrelated
3-4 = Partially relevant
5-6 = Generally relevant but misses important parts
7-8 = Clearly relevant and addresses most requirements
9 = Highly relevant and comprehensive
10 = Directly addresses every important part with exceptional focus


============================================================
2. CLARITY
============================================================

Is the answer easy to understand, well organized, and logically structured?

Scoring:

1-2 = Very confusing
3-4 = Difficult to follow
5-6 = Understandable but has organization or explanation problems
7-8 = Clear and well organized
9 = Very clear and easy to follow
10 = Exceptionally clear, precise, and logically structured


============================================================
3. ACTIONABILITY
============================================================

Can the user actually use the recommendations?

Scoring:

1-2 = No useful actions
3-4 = Very vague suggestions
5-6 = Some useful suggestions but lacks concrete steps
7-8 = Provides several practical steps
9 = Very practical with clear next actions
10 = Extremely actionable, specific, realistic, and easy to execute


============================================================
4. ACCURACY
============================================================

Are the technical and factual claims reasonable and free from obvious errors?

Scoring:

1-2 = Many serious errors
3-4 = Several questionable claims
5-6 = Mostly correct but contains some questionable information
7-8 = Generally accurate
9 = Very accurate with only minor issues
10 = Exceptionally accurate with no meaningful factual or technical issues


============================================================
5. COMPLETENESS
============================================================

Does the answer cover the important aspects needed to properly
answer the user's question?

Scoring:

1-2 = Leaves out most important information
3-4 = Covers only a small part of the question
5-6 = Covers the basic question but misses several important areas
7-8 = Covers most important areas but has some meaningful gaps
9 = Covers almost all important aspects with only minor gaps
10 = Covers all major aspects required by the question with no meaningful gaps

Look specifically for:

- Important topics that are missing
- Important practical considerations that are ignored
- Missing parts of a multi-part question
- Areas that the user would reasonably expect to be covered

Do NOT penalize the answer for information that is genuinely
unnecessary for the user's question.


============================================================
IMPORTANT SCORING RULES
============================================================

- Be strict.
- Do not give 10 unless the answer genuinely deserves an exceptional score.
- A good answer does NOT automatically deserve 10.
- Look for missing information, vague recommendations,
  unnecessary information, repetition, questionable claims,
  and technical inaccuracies.
- Scores should reflect the actual answer, not what the answer
  could have been.
- Do not reward an answer simply because it is long.
- More detail is useful only when the detail is relevant and accurate.
- If there are weaknesses, mention them in the feedback.
- Different answers should receive different scores when their
  quality differs.
- Do not intentionally make scores different.
- Score based on the actual quality of the answer.


============================================================
OVERALL SCORE
============================================================

Calculate the overall score as:

(relevance + clarity + actionability + accuracy + completeness) / 5

Round the overall score to one decimal place.


============================================================
FEEDBACK
============================================================

Provide concise feedback explaining:

1. The strongest part of the answer.
2. The biggest weakness.
3. One specific improvement that would make the answer better.


============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.
Do not write anything outside the JSON.

Use exactly this structure:

{{
    "relevance": 0,
    "clarity": 0,
    "actionability": 0,
    "accuracy": 0,
    "completeness": 0,
    "overall": 0.0,
    "feedback": ""
}}
"""

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=evaluation_prompt
    )

    output = response.output_text.strip()

    # --------------------------------------------------------
    # Convert evaluator response into JSON
    # --------------------------------------------------------

    try:

        return json.loads(output)

    except json.JSONDecodeError:

        print("\nERROR: Evaluator returned invalid JSON.")
        print("Raw evaluator output:")
        print(output)

        return {
            "relevance": 0,
            "clarity": 0,
            "actionability": 0,
            "accuracy": 0,
            "completeness": 0,
            "overall": 0.0,
            "feedback": "Evaluator returned invalid JSON."
        }


# ============================================================
# 7. STORE RESULTS
# ============================================================

results = {}


# ============================================================
# 8. RUN THE EXPERIMENT
# ============================================================

for name, prompt in prompts.items():

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    answer = generate_answer(prompt)

    print("\nGenerated Answer:")
    print(answer)

    # --------------------------------------------------------
    # Evaluate answer
    # --------------------------------------------------------

    evaluation = evaluate_answer(
        question,
        answer
    )

    results[name] = evaluation

    print("\nEvaluation:")

    print(
        json.dumps(
            evaluation,
            indent=4
        )
    )


# ============================================================
# 9. COMPARE PROMPTS
# ============================================================

print("\n")
print("=" * 90)
print("PROMPT COMPARISON")
print("=" * 90)

print(
    f"{'Prompt':<20}"
    f"{'Relevance':<12}"
    f"{'Clarity':<12}"
    f"{'Actionability':<15}"
    f"{'Accuracy':<12}"
    f"{'Completeness':<15}"
    f"{'Overall':<10}"
)

print("-" * 90)

for name, evaluation in results.items():

    print(
        f"{name:<20}"
        f"{evaluation['relevance']:<12}"
        f"{evaluation['clarity']:<12}"
        f"{evaluation['actionability']:<15}"
        f"{evaluation['accuracy']:<12}"
        f"{evaluation['completeness']:<15}"
        f"{evaluation['overall']:<10}"
    )


# ============================================================
# 10. SHOW FEEDBACK
# ============================================================

print("\n")
print("=" * 75)
print("DETAILED FEEDBACK")
print("=" * 75)

for name, evaluation in results.items():

    print(f"\n{name}:")
    print(evaluation["feedback"])
