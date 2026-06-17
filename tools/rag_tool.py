"""
tools/rag_tool.py — RAG (Retrieval-Augmented Generation) layer

What this does:
  1. Accepts brand documents (PDF, TXT, MD) from a folder path
  2. Splits them into chunks
  3. Embeds chunks using a local HuggingFace model (free, no API key needed)
  4. Stores embeddings in ChromaDB (local vector database)
  5. On every blog generation — retrieves the most relevant chunks
     and returns them as brand_context to inject into the prompt

Why this matters:
  Without RAG → blog sounds like generic AI output
  With RAG    → blog reflects actual brand voice, real product details,
                accurate pricing, real USPs from the company's own docs
"""

import os
import cohere
from pathlib import Path

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────

CHROMA_PERSIST_DIR = "chroma_store"
TOP_K = 3
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50
co = cohere.Client(os.getenv("COHERE_API_KEY"))

class CohereEmbeddings:
    """
    Wrapper to match LangChain's embedding interface using Cohere's API.
    Replaces local HuggingFace model loading — no in-memory model,
    so no OOM risk on memory-constrained deployments.
    """
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = co.embed(
            texts=texts,
            model="embed-english-v3.0",
            input_type="search_document",
        )
        return response.embeddings

    def embed_query(self, text: str) -> list[float]:
        response = co.embed(
            texts=[text],
            model="embed-english-v3.0",
            input_type="search_query",
        )
        return response.embeddings[0]

# ── LOADER ────────────────────────────────────────────────────────────────────

def load_documents(docs_path: str) -> list:
    """
    Loads all supported files from a folder.
    Supports: .txt, .pdf, .md

    docs_path — path to the folder containing brand documents.
    Example files a company might upload:
        - brand_guidelines.pdf
        - product_descriptions.txt
        - past_blogs.md
        - pricing.txt
    """
    path = Path(docs_path)
    if not path.exists():
        print(f"[RAG] Docs path '{docs_path}' not found — skipping RAG.")
        return []

    docs = []
    supported = {".txt": TextLoader, ".pdf": PyPDFLoader, ".md": UnstructuredMarkdownLoader}

    for file in path.iterdir():
        ext = file.suffix.lower()
        if ext not in supported:
            continue
        try:
            loader = supported[ext](str(file))
            loaded = loader.load()
            docs.extend(loaded)
            print(f"[RAG] Loaded: {file.name} ({len(loaded)} chunks raw)")
        except Exception as e:
            print(f"[RAG] Could not load {file.name}: {e}")

    return docs


# ── CHUNKER ───────────────────────────────────────────────────────────────────

def split_documents(docs: list) -> list:
    """
    Splits raw documents into smaller overlapping chunks.
    RecursiveCharacterTextSplitter tries to split on paragraphs,
    then sentences, then words — keeps semantic meaning intact.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Split into {len(chunks)} chunks")
    return chunks


# ── VECTOR STORE ──────────────────────────────────────────────────────────────

def build_vectorstore(chunks: list, company_name: str) -> Chroma:
    embeddings = CohereEmbeddings()
    collection_name = company_name.lower().replace(" ", "_")[:50]

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print(f"[RAG] Vectorstore built for '{company_name}' — {len(chunks)} chunks stored")

    return vectorstore

def load_vectorstore(company_name: str) -> Chroma | None:
    persist_path = Path(CHROMA_PERSIST_DIR)
    if not persist_path.exists():
        return None

    try:
        embeddings = CohereEmbeddings()
        collection_name = company_name.lower().replace(" ", "_")[:50]
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        print(f"[RAG] Loaded existing vectorstore for '{company_name}'")
        return vectorstore
    except Exception as e:
        print(f"[RAG] Could not load vectorstore: {e}")
        return None

# ── RETRIEVER ─────────────────────────────────────────────────────────────────

def retrieve_brand_context(
    vectorstore: Chroma,
    keyword: str,
    niche: str,
    company_name: str,
) -> str:
    """
    Retrieves the most relevant brand chunks for a given keyword.
    Returns them as a single string to inject into the blog prompt
    as brand_context.

    The query combines keyword + niche + company so retrieval
    is specific to what the blog post is actually about.
    """
    query = f"{company_name} {niche} {keyword}"

    try:
        results = vectorstore.similarity_search(query, k=TOP_K)
        if not results:
            return ""

        # Join retrieved chunks with clear separators
        context_parts = [doc.page_content.strip() for doc in results]
        brand_context = "\n\n---\n\n".join(context_parts)
        print(f"[RAG] Retrieved {len(results)} chunks for: '{keyword}'")
        return brand_context

    except Exception as e:
        print(f"[RAG] Retrieval failed: {e}")
        return ""


# HIGH-LEVEL INTERFACE 
# These two functions are what main.py and crew.py will actually call.
# Everything above is internal implementation.

def setup_rag(docs_path: str, company_name: str) -> Chroma | None:
    """
    Call this ONCE at startup when the company provides brand docs.

    1. Loads all docs from docs_path
    2. Splits into chunks
    3. Builds + persists vectorstore

    Returns the vectorstore object, or None if no docs were found.

    Usage in main.py:
        vectorstore = setup_rag("brand_docs/", "Acme Corp")
    """
    docs = load_documents(docs_path)
    if not docs:
        print("[RAG] No documents loaded — running without brand context.")
        return None

    chunks = split_documents(docs)
    vectorstore = build_vectorstore(chunks, company_name)
    return vectorstore


def get_brand_context(
    vectorstore: Chroma | None,
    keyword: str,
    niche: str,
    company_name: str,
) -> str:
    """
    Call this BEFORE every blog generation.

    If vectorstore is None (no docs uploaded) → returns empty string
    → blog_generator runs normally without brand context.

    If vectorstore exists → retrieves relevant chunks
    → injects into blog prompt via brand_context parameter.

    Usage in main.py / crew.py:
        context = get_brand_context(vectorstore, keyword, niche, company_name)
        blog = generate_blog(..., brand_context=context)
    """
    if vectorstore is None:
        return ""
    return retrieve_brand_context(vectorstore, keyword, niche, company_name)