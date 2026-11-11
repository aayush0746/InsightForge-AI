# Sample document
document = """
Students must maintain at least 75% attendance.
Students below the required attendance may not be
allowed to appear for examinations.

Students can apply for leave by submitting a leave
application to their concerned faculty member.

The library remains open from 9 AM to 6 PM.
Students can borrow up to 3 books at a time.
"""


# Split document into words
words = document.split()


# Number of words in each chunk
chunk_size = 20


# Number of words shared between chunks
overlap = 5


# Store chunks
chunks = []


# Start position
start = 0


while start < len(words):

    # End position of current chunk
    end = start + chunk_size

    # Create chunk
    chunk = " ".join(words[start:end])

    chunks.append(chunk)

    # Move forward but keep overlap
    start += chunk_size - overlap


# Display chunks
print("Total chunks:", len(chunks))

for i, chunk in enumerate(chunks):

    print(f"\nChunk {i + 1}:")
    print(chunk)