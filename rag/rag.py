import os
import re
import sys
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION = "enterprise_docs"
LLM_MODEL = "qwen2.5:3b"
EMBED_MODEL = "bge-m3"
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
REFUS = "Je n'ai pas trouvé cette information dans les documents disponibles."
SEUIL = 0.55
ROLES = ["employe", "manager", "rh", "finance", "admin"]

client = QdrantClient(url=QDRANT_URL)
store = QdrantVectorStore(client=client, collection_name=COLLECTION,
                          embedding=OllamaEmbeddings(model=EMBED_MODEL))
llm = ChatOllama(model=LLM_MODEL, temperature=0)


def construire_filtre(role):
    """Filtre appliqué AVANT la recherche : version actuelle + rôle autorisé."""
    if role not in ROLES:
        raise ValueError(f"Rôle inconnu : {role}")
    return Filter(must=[
        FieldCondition(key="metadata.statut", match=MatchValue(value="actuelle")),
        FieldCondition(key="metadata.roles_autorises", match=MatchValue(value=role)),
    ])


def retrieve_scored(question, role, k=4):
    return store.similarity_search_with_score(
        question, k=k, filter=construire_filtre(role))


STOP = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "en", "au",
        "aux", "est", "sont", "que", "qui", "quel", "quelle", "quels", "quelles",
        "chez", "pour", "par", "dans", "sur", "ce", "cette", "ces", "il", "je",
        "mon", "ma", "mes", "comment", "combien", "avec", "sans", "se", "sa",
        "son", "ses", "novatech", "solutions"}


def tokens(texte):
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in STOP and len(w) > 1]


_cache = {}


def corpus(role):
    """Charge les passages autorisés pour ce rôle et construit l'index BM25."""
    if role not in _cache:
        docs, offset = [], None
        while True:
            points, offset = client.scroll(
                COLLECTION, scroll_filter=construire_filtre(role), limit=256,
                offset=offset, with_payload=True, with_vectors=False)
            docs += [Document(page_content=p.payload["page_content"],
                              metadata=p.payload["metadata"]) for p in points]
            if offset is None:
                break
        _cache[role] = (docs, BM25Okapi([tokens(d.page_content) for d in docs]))
    return _cache[role]


def retrieve_hybrid(question, role, k=4, n=20, rrf_k=60):
    """Fusionne le classement vectoriel et le classement BM25 (RRF)."""
    dense = store.similarity_search_with_score(
        question, k=n, filter=construire_filtre(role))
    docs, bm25 = corpus(role)
    scores = bm25.get_scores(tokens(question))
    ordre = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:n]
    sparse = [docs[i] for i in ordre if scores[i] > 0]

    def cle(d):
        return (d.metadata["doc_id"], d.metadata["chunk_index"])

    fusion, par_cle = {}, {}
    for liste in ([d for d, _ in dense], sparse):
        for rang, d in enumerate(liste, start=1):
            fusion[cle(d)] = fusion.get(cle(d), 0) + 1 / (rrf_k + rang)
            par_cle[cle(d)] = d
    top = sorted(fusion, key=fusion.get, reverse=True)[:k]
    meilleur_score = dense[0][1] if dense else 0
    return [par_cle[c] for c in top], meilleur_score


_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL)
    return _reranker


def retrieve_reranked(question, role, k=4, n=15):
    """Hybride (n candidats) puis reclassement par le cross-encoder."""
    docs, score_vec = retrieve_hybrid(question, role, k=n)
    if not docs:
        return [], score_vec, []
    scores = get_reranker().predict([(question, d.page_content) for d in docs])
    ordre = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:k]
    return [docs[i] for i in ordre], score_vec, [float(scores[i]) for i in ordre]


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


def answer(question, role, k=4):
    docs, meilleur = retrieve_hybrid(question, role, k)
    if not docs or meilleur < SEUIL:
        return {"reponse": REFUS, "sources": [], "score": meilleur}
    reponse = llm.invoke(construire_prompt(question, docs)).content.strip()
    if REFUS in reponse:
        return {"reponse": REFUS, "sources": [], "score": meilleur}
    cites = {int(n) for n in re.findall(r"\[(\d+)\]", reponse)}
    if not cites:
        return {"reponse": REFUS, "sources": [], "score": meilleur}
    sources = [{
        "n": i,
        "doc_id": d.metadata["doc_id"],
        "titre": d.metadata["titre"],
        "version": d.metadata["version"],
        "section": d.metadata["section"],
    } for i, d in enumerate(docs, start=1) if i in cites]
    return {"reponse": reponse, "sources": sources, "score": meilleur}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ROLES:
        sys.exit(f"Usage : python rag/rag.py <role> \"question\"   (rôles : {', '.join(ROLES)})")
    role = sys.argv[1]
    question = " ".join(sys.argv[2:]) or input("Question : ")
    resultat = answer(question, role)
    print(f"(rôle : {role} | score du meilleur passage : {resultat['score']:.3f})")
    print("\nRéponse :\n" + resultat["reponse"])
    print("\nSources :")
    for s in resultat["sources"]:
        print(f"  [{s['n']}] {s['doc_id']} v{s['version']} - {s['titre']} - {s['section']}")