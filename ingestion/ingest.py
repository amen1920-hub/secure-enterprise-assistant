import argparse
import os
import uuid
import yaml
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from chunker import decouper, lire_document

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION = "enterprise_docs"
EMBED_MODEL = "bge-m3"
DIM = 1024

MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"


def preparer_collection(client, reset):
    existe = client.collection_exists(COLLECTION)
    if existe and reset:
        client.delete_collection(COLLECTION)
        existe = False
    if not existe:
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )
        for champ in ("roles_autorises", "statut", "doc_id", "departement"):
            client.create_payload_index(
                COLLECTION, f"metadata.{champ}", PayloadSchemaType.KEYWORD
            )
        print(f"Collection '{COLLECTION}' créée")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Supprime et recrée la collection")
    args = parser.parse_args()

    client = QdrantClient(url=QDRANT_URL)
    preparer_collection(client, args.reset)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    store = QdrantVectorStore(
        client=client, collection_name=COLLECTION, embedding=embeddings
    )

    docs = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["documents"]
    total = 0
    for i, d in enumerate(docs, start=1):
        statut = d.get("statut", "actuelle")
        chunks = decouper(lire_document(RAW / f"{d['id']}.md"))
        documents, ids = [], []
        for n, (section, texte) in enumerate(chunks):
            documents.append(Document(
                page_content=f"{d['titre']} (version {d['version']}) - {section}\n{texte}",
                metadata={
                    "doc_id": d["id"],
                    "titre": d["titre"],
                    "departement": d["departement"],
                    "confidentialite": d["confidentialite"],
                    "roles_autorises": d["roles_autorises"],
                    "version": d["version"],
                    "date": d["date"],
                    "statut": statut,
                    "famille": d.get("famille", d["id"]),
                    "section": section,
                    "chunk_index": n,
                },
            ))
            ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{d['id']}:{n}")))
        store.add_documents(documents, ids=ids)
        total += len(documents)
        print(f"[{i}/{len(docs)}] {d['id']:12} {len(documents)} chunks")

    print(f"\n{total} chunks envoyés. Points dans Qdrant : "
          f"{client.count(COLLECTION).count}")

    print("\nTest de recherche : « Combien de jours de congés payés par an ? »")
    for r in store.similarity_search("Combien de jours de congés payés par an ?", k=4):
        m = r.metadata
        print(f"  {m['doc_id']:12} v{m['version']} ({m['statut']}) - {m['section']}")


if __name__ == "__main__":
    main()