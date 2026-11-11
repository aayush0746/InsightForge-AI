import os
import chromadb

from dotenv import load_dotenv
from google import genai


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found")


# ============================================================
# 2. CREATE GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=api_key
)


# ============================================================
# 3. CREATE CHROMADB CLIENT
# ============================================================

chroma_client = chromadb.Client()


# ============================================================
# 4. CREATE COLLECTION
# ============================================================

collection = chroma_client.create_collection(
    name="student_information"
)


# ============================================================
# 5. DOCUMENT CHUNKS
# ============================================================

chunks = [
    "Students must maintain at least 75% attendance.",

    "Students can apply for leave by submitting a leave application to their concerned faculty member.",

    "The library remains open from 9 AM to 6 PM.",

    "Students can borrow up to 3 books at a time."
]


# ============================================================
# 6. STORE DOCUMENTS
# ============================================================

collection.add(
    documents=chunks,

    ids=[
        "chunk1",
        "chunk2",
        "chunk3",
        "chunk4"
    ]
)


# ============================================================
# 7. USER QUESTION
# ============================================================

question = "How can I apply for leave?"


# ============================================================
# 8. SEARCH VECTOR DATABASE
# ============================================================

results = collection.query(
    query_texts=[question],
    n_results=2
)


# ============================================================
# 9. GET RETRIEVED DOCUMENTS
# ============================================================

relevant_documents = results["documents"][0]


print("\nQuestion:")
print(question)


print("\nRetrieved Documents:")

for document in relevant_documents:
    print("-", document)


# ============================================================
# 10. CREATE CONTEXT
# ============================================================

context = "\n".join(relevant_documents)


# ============================================================
# 11. CREATE RAG PROMPT
# ============================================================

prompt = f"""
You are an AI assistant.

Answer the user's question using ONLY the
information provided in the context.

Context:
{context}

User Question:
{question}

If the context does not contain enough information,
say that the information is not available.
"""


# ============================================================
# 12. SEND CONTEXT TO GEMINI
# ============================================================

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)


# ============================================================
# 13. FINAL ANSWER
# ============================================================

print("\nFinal Answer:")
print(response.output_text)