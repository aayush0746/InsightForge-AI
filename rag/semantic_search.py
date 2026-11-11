from sentence_transformers import SentenceTransformer, util

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Our question
query = "How can I apply for leave?"

# Documents
documents = [
    "What is the procedure for taking absence?",
    "Students can borrow books from the library.",
    "Students need permission from faculty for leave."
]

# Create embedding for the question
query_embedding = model.encode(query, convert_to_tensor=True)

# Create embeddings for documents
document_embeddings = model.encode(
    documents,
    convert_to_tensor=True
)

# Calculate similarity
similarities = util.cos_sim(
    query_embedding,
    document_embeddings
)[0]

# Display results
for document, score in zip(documents, similarities):

    print("\nDocument:")
    print(document)

    print("Similarity score:")
    print(float(score))