import argparse
import hashlib
import json
import logging
import os
import uuid
import yaml
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, FieldCondition, Filter, FilterSelector,
    MatchValue, PayloadSchemaType, VectorParams,
)

from chunker import decouper, lire_document

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ingestion")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION = "enterprise_docs"
EMBED_MODEL = "bge-m3"
DIM = 1024

MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"

CLES_HASH = ["titre", "departement", "confidentialite", "roles_autorises",
             "version", "date", "statut", "famille"]


def calculer_hash(d, texte):
    meta = json.dumps({k: d.get(k) for k in CLES_HASH},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((meta + texte).encode("utf-8")).hexdigest()


def filtre_doc(doc_id):
    return Filter(must=[FieldCondition(
        key="metadata.doc_id", match=MatchValue(value=doc_id))])


def hash_indexe(client, doc_id):
    points, _ = client.scroll(COLLECTION, scroll_filter=filtre_doc(doc_id),
                              limit=1, with_payload=True)
    if not points:
        return None
    return points[0].payload.get("metadata", {}).get("content_hash")


def ids_indexes(client):
    ids, offset = set(), None
    while True:
        points, offset = client.scroll(COLLECTION, limit=256, offset=offset,
                                       with_payload=True, with_vectors=False)
        ids.update(p.payload["metadata"]["doc_id"] for p in points)
        if offset is None:
            return ids


def supprimer_doc(client, doc_id):
    client.delete(COLLECTION,
                  points_selector=FilterSelector(filter=filtre_doc(doc_id)))


def preparer_collection(client, reset):
    existe = client.collection_exists(COLLECTION)
    if existe and reset:
        client.delete_collection(COLLECTION)
        existe = False
    if not existe:
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))
        for champ in ("roles_autorises", "statut", "doc_id", "departement"):
            client.create_payload_index(
                COLLECTION, f"metadata.{champ}", PayloadSchemaType.KEYWORD)
        log.info("Collection '%s' créée", COLLECTION)


def construire_chunks(d, texte, empreinte):
    documents, ids = [], []
    for n, (section, contenu) in enumerate(decouper(texte)):
        documents.append(Document(
            page_content=f"{d['titre']} (version {d['version']}) - {section}\n{contenu}",
            metadata={
                "doc_id": d["id"],
                "titre": d["titre"],
                "departement": d["departement"],
                "confidentialite": d["confidentialite"],
                "roles_autorises": d["roles_autorises"],
                "version": d["version"],
                "date": d["date"],
                "statut": d.get("statut", "actuelle"),
                "famille": d.get("famille", d["id"]),
                "section": section,
                "chunk_index": n,
                "content_hash": empreinte,
            }))
        ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{d['id']}:{n}")))
    return documents, ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Supprime et recrée la collection")
    args = parser.parse_args()

    client = QdrantClient(url=QDRANT_URL)
    preparer_collection(client, args.reset)
    store = QdrantVectorStore(client=client, collection_name=COLLECTION,
                              embedding=OllamaEmbeddings(model=EMBED_MODEL))

    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    stats = {"ajoutés": 0, "modifiés": 0, "inchangés": 0, "supprimés": 0}

    for d in docs:
        texte = lire_document(RAW / f"{d['id']}.md")
        empreinte = calculer_hash(d, texte)
        ancien = hash_indexe(client, d["id"])
        if ancien == empreinte:
            stats["inchangés"] += 1
            continue
        if ancien is not None:
            supprimer_doc(client, d["id"])
            stats["modifiés"] += 1
            etat = "modifié"
        else:
            stats["ajoutés"] += 1
            etat = "ajouté"
        documents, ids = construire_chunks(d, texte, empreinte)
        store.add_documents(documents, ids=ids)
        log.info("%-9s %-12s %d chunks", etat, d["id"], len(documents))

    ids_manifeste = {d["id"] for d in docs}
    for doc_id in sorted(ids_indexes(client) - ids_manifeste):
        supprimer_doc(client, doc_id)
        stats["supprimés"] += 1
        log.info("supprimé  %s (absent du manifeste)", doc_id)

    log.info("\nBilan : %s", stats)
    log.info("Points dans Qdrant : %d", client.count(COLLECTION).count)


if __name__ == "__main__":
    main()