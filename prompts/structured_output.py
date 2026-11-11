import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

user_question = "How can Generative AI help a college student get a job?"

prompt = f"""
You are an expert career consultant.

Analyze the following question:

{user_question}

Return the answer ONLY as valid JSON.

The JSON must contain exactly these fields:

{{
    "skills": [],
    "use_cases": [],
    "action_plan": [],
    "recommended_projects": []
}}

Do not add explanations outside the JSON.
"""

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)

result = json.loads(response.output_text)

print("\nSkills:")
print(result["skills"])

print("\nUse Cases:")
print(result["use_cases"])

print("\nAction Plan:")
print(result["action_plan"])

print("\nRecommended Projects:")
print(result["recommended_projects"])