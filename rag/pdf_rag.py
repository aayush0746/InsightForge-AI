import os
import re
import chromadb

from dotenv import load_dotenv
from pypdf import PdfReader
from google import genai


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found")

client = genai.Client(
    api_key=api_key
)


# ============================================================
# 2. PDF INFORMATION
# ============================================================

pdf_path = "documents/college_rules.pdf"
pdf_name = "college_rules.pdf"


# ============================================================
# 3. READ PDF
# ============================================================

reader = PdfReader(pdf_path)

print("Total PDF pages:", len(reader.pages))


# ============================================================
# 4. EXTRACT TEXT PAGE BY PAGE
# ============================================================

pages = []

for page_number, page in enumerate(reader.pages, start=1):

    page_text = page.extract_text()

    if page_text:
        pages.append({
            "page": page_number,
            "text": page_text
        })


# ============================================================
# 5. CHUNK SETTINGS
# ============================================================

chunk_size = 80
overlap_sentences = 1


# ============================================================
# 6. CREATE SENTENCE-BASED CHUNKS
# ============================================================

chunks = []
metadatas = []
ids = []

chunk_id = 0


for page in pages:

    text = page["text"]

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Split approximately by sentence boundaries
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    current_chunk = []
    current_word_count = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        sentence_word_count = len(
            sentence.split()
        )

        # If adding the sentence would make
        # the chunk too large, save current chunk
        if (
            current_chunk
            and current_word_count + sentence_word_count
            > chunk_size
        ):

            chunk_text = " ".join(
                current_chunk
            )

            chunks.append(chunk_text)

            metadatas.append({
                "source": pdf_name,
                "page": page["page"],
                "chunk_id": chunk_id
            })

            ids.append(
                f"chunk_{chunk_id}"
            )

            chunk_id += 1

            # Keep the last sentence as overlap
            current_chunk = current_chunk[
                -overlap_sentences:
            ]

            current_word_count = sum(
                len(sentence.split())
                for sentence in current_chunk
            )

        current_chunk.append(sentence)

        current_word_count += sentence_word_count


    # Store remaining sentences
    if current_chunk:

        chunk_text = " ".join(
            current_chunk
        )

        chunks.append(chunk_text)

        metadatas.append({
            "source": pdf_name,
            "page": page["page"],
            "chunk_id": chunk_id
        })

        ids.append(
            f"chunk_{chunk_id}"
        )

        chunk_id += 1


# ============================================================
# 7. DISPLAY CHUNKS
# ============================================================

print("\nTotal chunks:", len(chunks))

for i, chunk in enumerate(chunks):

    print("\n========================================")
    print(f"Chunk {i + 1}")
    print("========================================")

    print(chunk)


# ============================================================
# 8. CREATE CHROMADB
# ============================================================

chroma_client = chromadb.Client()

collection = chroma_client.create_collection(
    name="infoccepts_document_v3"
)


# ============================================================
# 9. STORE CHUNKS + METADATA
# ============================================================

collection.add(
    documents=chunks,
    metadatas=metadatas,
    ids=ids
)


print("\nChunks successfully stored in ChromaDB!")


# ============================================================
# 10. USER QUESTION
# ============================================================

question = "What is the company's office in London?"


# ============================================================
# 11. SEARCH
# ============================================================

results = collection.query(
    query_texts=[question],
    n_results=2
)


# ============================================================
# 12. RETRIEVE RESULTS
# ============================================================

relevant_documents = results["documents"][0]

relevant_metadata = results["metadatas"][0]


print("\nQuestion:")
print(question)


print("\nRetrieved Chunks:")

for document, metadata in zip(
    relevant_documents,
    relevant_metadata
):

    print("\n--------------------------------")
    print("Source:", metadata["source"])
    print("Page:", metadata["page"])
    print("Chunk ID:", metadata["chunk_id"])

    print("\nContent:")
    print(document)


# ============================================================
# 13. CREATE CONTEXT
# ============================================================

context_parts = []

for document, metadata in zip(
    relevant_documents,
    relevant_metadata
):

    context_parts.append(
        f"""
Source: {metadata["source"]}
Page: {metadata["page"]}
Chunk: {metadata["chunk_id"]}

Content:
{document}
"""
    )


context = "\n".join(
    context_parts
)


# ============================================================
# 14. CREATE RAG PROMPT
# ============================================================

prompt = f"""
You are an AI assistant answering questions
using the provided document.

Use ONLY the information in the context.

Context:
{context}

Question:
{question}

Give a clear and concise answer.

At the end provide the sources:

Sources:
- filename, page number

If the information is not available,
say:

"Information not available in the document."
"""


# ============================================================
# 15. ASK GEMINI
# ============================================================

response = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)


# ============================================================
# 16. FINAL ANSWER
# ============================================================

print("\n========================================")
print("FINAL ANSWER")
print("========================================")

print(response.output_text)