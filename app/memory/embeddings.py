from sentence_transformers import SentenceTransformer

# Load the model once when the module is imported.
# This avoids reloading it on every function call which would be slow.
# all-MiniLM-L6-v2 is fast, small (~80MB), and good quality for short text.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding(text: str) -> list[float]:
    """
    Converts text into a 384-dimensional vector embedding.
    Similar text will produce similar vectors — this is what
    powers our semantic search in the Memory OS.
    """
    embedding = _model.encode(text)
    return embedding.tolist()