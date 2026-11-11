import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

user_question = "How can AI help businesses?"

prompt = f"""
My name is aayush gupta 
I am  a software enginner  in al ml

Answer the following question:
 
How can i improve  my skills ?

{user_question}

Give a clear and practical answer.
"""

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)

print(response.output_text)