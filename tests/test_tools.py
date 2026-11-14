import pytest
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def charger():
    chemin = ROOT / "data" / "manifest.yaml"
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))["documents"]


@pytest.fixture(scope="module")
def tools():
    try:
        import tools as module
        module.rag.client.get_collections()
    except Exception as e:
        pytest.skip(f"Qdrant ou Ollama indisponible : {e}")
    return module


def test_permissions_de_l_employe_excluent_les_documents_confidentiels(tools):
    ids = {d["doc_id"] for d in tools.get_user_permissions("employe")["documents"]}
    assert "RHC-001" not in ids
    assert "RH-001" in ids


def test_permissions_de_rh_incluent_la_grille_des_salaires(tools):
    ids = {d["doc_id"] for d in tools.get_user_permissions("rh")["documents"]}
    assert "RHC-001" in ids


def test_permissions_correspondent_au_manifeste(tools):
    for role in ("employe", "manager", "rh", "finance", "admin"):
        attendu = {d["id"] for d in charger()
                   if role in d["roles_autorises"]
                   and d.get("statut", "actuelle") == "actuelle"}
        obtenu = {d["doc_id"] for d in tools.get_user_permissions(role)["documents"]}
        assert obtenu == attendu, role


def test_metadonnees_accessibles_pour_rh(tools):
    m = tools.get_document_metadata("RHC-001", "rh")
    assert m["doc_id"] == "RHC-001" and m["confidentialite"] == "confidentiel"


def test_metadonnees_interdites_ne_revelent_rien(tools):
    interdit = tools.get_document_metadata("RHC-001", "employe")
    inexistant = tools.get_document_metadata("XXX-999", "employe")
    assert interdit == inexistant == {"erreur": tools.INTROUVABLE}


def test_recherche_de_l_employe_ne_renvoie_aucun_document_confidentiel(tools):
    r = tools.search_documents("Quels sont les niveaux de salaires ?", "employe")
    assert not any(p["doc_id"].startswith("RHC-") for p in r["passages"])


def test_recherche_de_rh_renvoie_la_grille_des_salaires(tools):
    r = tools.search_documents("Quels sont les niveaux de salaires ?", "rh")
    assert any(p["doc_id"] == "RHC-001" for p in r["passages"])


def test_role_inconnu_renvoie_une_erreur(tools):
    assert "erreur" in tools.search_documents("congés", "pirate")
    assert "erreur" in tools.get_user_permissions("pirate")
    assert "erreur" in tools.get_document_metadata("RH-001", "pirate")