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