import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION = "enterprise_docs"
LLM_MODEL = "qwen2.5:3b"
EMBED_MODEL = "bge-m3"
REFUS = "Je n'ai pas trouvé cette information dans les documents disponibles."

client = QdrantClient(url=QDRANT_URL)
store = QdrantVectorStore(client=client, collection_name=COLLECTION,
                          embedding=OllamaEmbeddings(model=EMBED_MODEL))
llm = ChatOllama(model=LLM_MODEL, temperature=0)


def retrieve(question, k=4):
    """Cherche les k passages les plus proches, uniquement dans les versions actuelles."""
    filtre = Filter(must=[FieldCondition(
        key="metadata.statut", match=MatchValue(value="actuelle"))])
    return store.similarity_search(question, k=k, filter=filtre)

def retrieve_scored(question, k=4):
    filtre = Filter(must=[FieldCondition(
        key="metadata.statut", match=MatchValue(value="actuelle"))])
    return store.similarity_search_with_score(question, k=k, filter=filtre)


def construire_prompt(question, docs):
    sources = "\n\n".join(
        f"[{i}] {d.metadata['titre']} (version {d.metadata['version']}) - "
        f"{d.metadata['section']}\n{d.page_content}"
        for i, d in enumerate(docs, start=1))
    return f"""Tu es l'assistant interne de NovaTech Solutions.
Réponds à la question en français, uniquement à partir des sources ci-dessous.

Règles :
- N'utilise que les informations présentes dans les sources.
- Cite chaque information avec le numéro de sa source, par exemple [1].
- Si les sources ne contiennent pas la réponse, réponds exactement : {REFUS}

SOURCES :
{sources}

QUESTION : {question}

RÉPONSE :"""


def answer(question, k=4):
    docs = retrieve(question, k)
    if not docs:
        return {"reponse": REFUS, "sources": []}
    reponse = llm.invoke(construire_prompt(question, docs)).content.strip()
    if REFUS in reponse:
        return {"reponse": REFUS, "sources": []}
    cites = {int(n) for n in re.findall(r"\[(\d+)\]", reponse)}
    sources = [{
        "n": i,
        "doc_id": d.metadata["doc_id"],
        "titre": d.metadata["titre"],
        "version": d.metadata["version"],
        "section": d.metadata["section"],
    } for i, d in enumerate(docs, start=1) if i in cites]
    return {"reponse": reponse, "sources": sources}
    docs = retrieve(question, k)
    if not docs:
        return {"reponse": REFUS, "sources": []}
    reponse = llm.invoke(construire_prompt(question, docs)).content.strip()
    sources = [{
        "n": i,
        "doc_id": d.metadata["doc_id"],
        "titre": d.metadata["titre"],
        "version": d.metadata["version"],
        "section": d.metadata["section"],
    } for i, d in enumerate(docs, start=1)]
    return {"reponse": reponse, "sources": sources}


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or input("Question : ")
    resultat = answer(question)
    print("\nRéponse :\n" + resultat["reponse"])
    print("\nSources :")
    for s in resultat["sources"]:
        print(f"  [{s['n']}] {s['doc_id']} v{s['version']} - {s['titre']} - {s['section']}")