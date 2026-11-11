from sentence_transformers import SentenceTransformer

# Load the embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Text we want to convert into an embedding
text = "How can I apply for leave?"

# Generate embedding
embedding = model.encode(text)

print("Text:")
print(text)

print("\nEmbedding:")
print(embedding)

print("\nNumber of values:")
print(len(embedding))