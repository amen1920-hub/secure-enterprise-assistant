from qdrant_client.models import FieldCondition, Filter, MatchValue
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
import rag  # noqa: E402

MANIFEST = ROOT / "data" / "manifest.yaml"
INTROUVABLE = "Document introuvable ou accès refusé."


def _documents():
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]


def search_documents(question: str, role: str, k: int = 4) -> dict:
    """Passages pertinents parmi les documents autorisés pour ce rôle."""
    if role not in rag.ROLES:
        return {"erreur": "Rôle inconnu."}
    docs, score = rag.retrieve_hybrid(question, role, k)
    if not docs or score < rag.SEUIL:
        return {"score": score, "passages": []}
    return {"score": score, "passages": [{
        "doc_id": d.metadata["doc_id"],
        "titre": d.metadata["titre"],
        "version": d.metadata["version"],
        "section": d.metadata["section"],
        "texte": d.page_content,
    } for d in docs]}


def get_user_permissions(role: str) -> dict:
    """Documents (versions actuelles) que ce rôle a le droit de consulter."""
    if role not in rag.ROLES:
        return {"erreur": "Rôle inconnu."}
    docs = [d for d in _documents()
            if role in d["roles_autorises"] and d.get("statut", "actuelle") == "actuelle"]
    return {"role": role, "nombre": len(docs), "documents": [{
        "doc_id": d["id"],
        "titre": d["titre"],
        "departement": d["departement"],
        "confidentialite": d["confidentialite"],
        "version": d["version"],
    } for d in docs]}


def get_document_metadata(doc_id: str, role: str) -> dict:
    """Métadonnées d'un document, seulement si le rôle y a accès."""
    if role not in rag.ROLES:
        return {"erreur": "Rôle inconnu."}
    for d in _documents():
        if d["id"] == doc_id and role in d["roles_autorises"]:
            return {
                "doc_id": d["id"],
                "titre": d["titre"],
                "departement": d["departement"],
                "confidentialite": d["confidentialite"],
                "version": d["version"],
                "date": d["date"],
                "statut": d.get("statut", "actuelle"),
            }
    return {"erreur": INTROUVABLE}
MAX_CARACTERES = 7000


def get_document_content(doc_id: str, role: str) -> dict:
    """Passages d'un document, dans l'ordre, seulement si le rôle y a accès.
    Le contrôle d'accès est dans le filtre Qdrant, avant toute lecture."""
    if role not in rag.ROLES:
        return {"erreur": "Rôle inconnu."}
    base = rag.construire_filtre(role)
    filtre = Filter(must=[*base.must, FieldCondition(
        key="metadata.doc_id", match=MatchValue(value=doc_id))])
    points, _ = rag.client.scroll(
        rag.COLLECTION, scroll_filter=filtre, limit=100,
        with_payload=True, with_vectors=False)
    if not points:
        return {"erreur": INTROUVABLE}
    points.sort(key=lambda p: p.payload["metadata"]["chunk_index"])
    passages, total = [], 0
    for p in points:
        texte = p.payload["page_content"]
        if total + len(texte) > MAX_CARACTERES:
            break
        total += len(texte)
        m = p.payload["metadata"]
        passages.append({
            "doc_id": m["doc_id"], "titre": m["titre"],
            "version": m["version"], "section": m["section"], "texte": texte,
        })
    return {"doc_id": doc_id, "passages": passages}