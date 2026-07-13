"""
knowledge_base.py
Turns the previously-hardcoded "safe instruments" string into a real,
retrieval-augmented knowledge base using ChromaDB (in-memory, no server/
persistence needed for a demo) with Google's embedding model as the
embedding function - so we reuse the same Gemini API key the user already
enters, instead of adding a second dependency/model download.

This is intentionally additive: if Chroma or the embedding call fails for
any reason (no network, bad key, etc.), callers should catch the exception
and fall back to the static instrument list in agents.py, so the app never
breaks because of this layer.
"""

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import google.generativeai as genai

COLLECTION_NAME = "wealth_instruments"
EMBED_MODEL = "models/text-embedding-004"

# The old single hardcoded paragraph, split into one retrievable chunk per
# instrument so retrieval can actually discriminate between them instead of
# always returning "the whole list" (which is what a plain string injection
# does today).
INSTRUMENT_DOCS = [
    {
        "id": "rd",
        "instrument": "Recurring Deposit (RD)",
        "text": (
            "Recurring Deposit (RD): guaranteed, fixed returns around 6-7% per "
            "annum. Best suited for building a monthly saving habit with small, "
            "consistent surplus amounts. Low risk, moderate lock-in, good "
            "starter instrument for someone new to investing or with modest "
            "monthly surplus."
        ),
    },
    {
        "id": "fd",
        "instrument": "Fixed Deposit (FD)",
        "text": (
            "Fixed Deposit (FD): guaranteed, fixed returns around 6.5-7.5% per "
            "annum. Best suited for a lump-sum surplus the user does not need "
            "immediate liquidity for. Low risk, low liquidity until maturity, "
            "good for a one-time bonus, refund, or accumulated surplus."
        ),
    },
    {
        "id": "ppf",
        "instrument": "Public Provident Fund (PPF)",
        "text": (
            "Public Provident Fund (PPF): government-backed, returns around "
            "7-8% per annum, long lock-in of 15 years, tax benefits under "
            "Section 80C. Best suited for long-term, goal-based saving (e.g. "
            "retirement) rather than a user who may need the money in the next "
            "few years. Low risk, low liquidity."
        ),
    },
    {
        "id": "debt_mf",
        "instrument": "Debt Mutual Funds",
        "text": (
            "Debt Mutual Funds: low-to-medium risk, historically around 7-9% "
            "per annum, more liquid than FD/PPF (can typically be redeemed in "
            "1-3 business days). Best suited for a user who wants better "
            "returns than a savings account but still wants to be able to "
            "access the money if needed."
        ),
    },
    {
        "id": "equity_sip",
        "instrument": "Large-cap Equity Mutual Funds (SIP)",
        "text": (
            "Large-cap Equity Mutual Fund SIP: medium risk, only appropriate "
            "if the user's surplus has been consistently positive for 3 or "
            "more months. Must always be framed as a long-term commitment of "
            "5+ years. Hard rule: never allocate more than 20% of the user's "
            "surplus to this instrument, regardless of how positive their "
            "surplus is."
        ),
    },
]


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Embeds text using the Gemini embedding model, reusing the user's own API key."""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            result = genai.embed_content(
                model=EMBED_MODEL,
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])
        return embeddings


def build_knowledge_base(api_key: str):
    """
    Builds (or rebuilds) an in-memory Chroma collection of instrument docs.
    Call once per session and cache the result (see app.py) - rebuilding on
    every chat message would mean an embedding API call per instrument per
    message, which is unnecessary and slow.
    """
    client = chromadb.EphemeralClient()
    # Fresh collection each call - avoids "already exists" errors on rerun.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=GeminiEmbeddingFunction(api_key),
    )
    collection.add(
        ids=[d["id"] for d in INSTRUMENT_DOCS],
        documents=[d["text"] for d in INSTRUMENT_DOCS],
        metadatas=[{"instrument": d["instrument"]} for d in INSTRUMENT_DOCS],
    )
    return collection


def retrieve_relevant_instruments(collection, query_text: str, k: int = 3) -> list[str]:
    """
    Returns up to k instrument doc texts most relevant to the query
    (typically the user's question + a snippet of their financial context).
    """
    results = collection.query(query_texts=[query_text], n_results=k)
    docs = results.get("documents", [[]])[0]
    return docs
