import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from google import genai


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")


# ============================================================
# 2. CREATE GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=api_key
)


# ============================================================
# 3. LOAD EMBEDDING MODEL
# ============================================================

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# ============================================================
# 4. OUR DOCUMENTS
# ============================================================

documents = [
    "Students can apply for leave by submitting a leave application.",
    "Students must provide a valid reason when requesting leave.",
    "Leave applications should be submitted to the concerned faculty member.",
    "Students can borrow books from the library.",
    "The library is open from 9 AM to 6 PM."
]


# ============================================================
# 5. USER QUESTION
# ============================================================

question = "How can I apply for leave?"


# ============================================================
# 6. CREATE EMBEDDING FOR THE QUESTION
# ============================================================

question_embedding = embedding_model.encode(
    question,
    convert_to_tensor=True
)


# ============================================================
# 7. CREATE EMBEDDINGS FOR DOCUMENTS
# ============================================================

document_embeddings = embedding_model.encode(
    documents,
    convert_to_tensor=True
)


# ============================================================
# 8. CALCULATE SIMILARITY
# ============================================================

similarities = util.cos_sim(
    question_embedding,
    document_embeddings
)[0]


# ============================================================
# 9. GET TOP RELEVANT DOCUMENTS
# ============================================================

top_results = similarities.topk(2)


relevant_documents = []

for index in top_results.indices:

    relevant_documents.append(
        documents[int(index)]
    )


# ============================================================
# 10. CREATE CONTEXT
# ============================================================

context = "\n".join(
    relevant_documents
)


# ============================================================
# 11. CREATE RAG PROMPT
# ============================================================

prompt = f"""
You are an assistant that answers questions using
the provided context.

Context:
{context}

Question:
{question}

Answer the question using only the provided context.

If the context does not contain enough information,
say that the information is not available.
"""


# ============================================================
# 12. SEND CONTEXT + QUESTION TO GEMINI
# ============================================================

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)


# ============================================================
# 13. PRINT RESULTS
# ============================================================

print("\nQuestion:")
print(question)

print("\nRetrieved Documents:")

for document in relevant_documents:
    print("-", document)

print("\nFinal Answer:")
print(response.output_text)