import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key = os.getenv("GEMINI_API_KEY")
)
question = """"
How  can a final-year  computer science student prepare
for a GenAi job?
"""
prompts = {
    "Basic Prompts" : f"""
{question}
""",
"Role Based Prompts" :f"""
You are and experienced GenAi career consultant.
{question}
Give practical and realistic recomemendations.

""",
"Advanded Prompts" : f"""
You are an  expert GenAi career consultant .
Analyze the following question:
{question}
Rules : 
-Recommend realistic skills.
-Give actionable recommendations.
-Avoid duplicate recommendations.
-Keep each recommendation consise.
-Do not invent qualifications or experience.
-Focus on Generative AI and Prompt Engineering .

"""

}
for name, prompt in prompts.items():
    response  = client.interactions.create(
        model = "gemini-3.6-flash",
        input = prompt
    )
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(response.output_text)