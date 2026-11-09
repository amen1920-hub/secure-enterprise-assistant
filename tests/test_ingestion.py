import os
import pytest
import yaml
from dotenv import load_dotenv
from pathlib import Path
from qdrant_client import QdrantClient

from chunker import decouper, lire_document

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION = "enterprise_docs"
CHAMPS = ["doc_id", "roles_autorises", "version", "statut", "section", "content_hash"]


def charger():
    chemin = ROOT / "data" / "manifest.yaml"
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))["documents"]


@pytest.fixture(scope="module")
def points():
    client = QdrantClient(url=URL)
    try:
        client.get_collections()
    except Exception:
        pytest.skip("Qdrant n'est pas joignable")
    if not client.collection_exists(COLLECTION):
        pytest.skip("Collection absente : lance ingestion/ingest.py")
    resultat, offset = [], None
    while True:
        lot, offset = client.scroll(COLLECTION, limit=256, offset=offset,
                                    with_payload=True, with_vectors=False)
        resultat += lot
        if offset is None:
            return resultat


def test_chaque_document_a_des_chunks():
    for d in charger():
        chunks = decouper(lire_document(ROOT / "data" / "raw" / f"{d['id']}.md"))
        assert len(chunks) >= 1, d["id"]
        assert all(len(c[1]) < 2000 for c in chunks), d["id"]


def test_nombre_de_points_correct(points):
    attendu = sum(
        len(decouper(lire_document(ROOT / "data" / "raw" / f"{d['id']}.md")))
        for d in charger()
    )
    assert len(points) == attendu


def test_tous_les_documents_sont_indexes(points):
    indexes = {p.payload["metadata"]["doc_id"] for p in points}
    assert indexes == {d["id"] for d in charger()}


def test_metadonnees_completes(points):
    for p in points:
        meta = p.payload["metadata"]
        for champ in CHAMPS:
            assert meta.get(champ) not in (None, "", []), (meta["doc_id"], champ)


def test_droits_identiques_au_manifeste(points):
    droits = {d["id"]: set(d["roles_autorises"]) for d in charger()}
    for p in points:
        meta = p.payload["metadata"]
        assert set(meta["roles_autorises"]) == droits[meta["doc_id"]], meta["doc_id"]


def test_statuts_coherents(points):
    for p in points:
        meta = p.payload["metadata"]
        assert meta["statut"] == ("obsolete" if meta["doc_id"].endswith("-V1") else "actuelle")