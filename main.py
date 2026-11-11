import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Create Gemini client
client = genai.Client(api_key=api_key)

# Send request using the Interactions API
response = client.interactions.create(
    model="gemini-3.6-flash",
    input="Explain Generative AI in simple words."
)

print("\nGemini Response:")
print(response.output_text)