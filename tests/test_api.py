import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
MOTS_DE_PASSE = {r: f"{r}-demo-2026" for r in ("employe", "manager", "rh", "finance", "admin")}


def connexion(role):
    r = client.post("/login", json={"email": f"{role}@novatech.tn",
                                     "password": MOTS_DE_PASSE[role]})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def services():
    try:
        import rag
        rag.client.get_collections()
        rag.store.embeddings.embed_query("test")
    except Exception as e:
        pytest.skip(f"Qdrant ou Ollama indisponible : {e}")


def test_connexion_renvoie_le_role_du_compte():
    r = client.post("/login", json={"email": "rh@novatech.tn", "password": "rh-demo-2026"})
    assert r.status_code == 200 and r.json()["role"] == "rh"


def test_mauvais_mot_de_passe_renvoie_401():
    r = client.post("/login", json={"email": "rh@novatech.tn", "password": "mauvais"})
    assert r.status_code == 401


def test_sans_jeton_l_acces_est_refuse():
    for url in ("/me", "/documents"):
        assert client.get(url).status_code == 401
    assert client.post("/ask", json={"question": "congés"}).status_code == 401


def test_jeton_modifie_est_refuse():
    jeton = connexion("employe")["Authorization"]
    faux = {"Authorization": jeton[:-3] + "xxx"}
    assert client.get("/me", headers=faux).status_code == 401


def test_me_renvoie_le_role_du_jeton():
    assert client.get("/me", headers=connexion("manager")).json()["role"] == "manager"


def test_envoyer_un_role_dans_la_question_est_rejete():
    r = client.post("/ask", headers=connexion("employe"),
                    json={"question": "congés", "role": "admin"})
    assert r.status_code == 422


def test_question_vide_ou_trop_longue_est_rejetee():
    h = connexion("employe")
    assert client.post("/ask", headers=h, json={"question": ""}).status_code == 422
    assert client.post("/ask", headers=h, json={"question": "a" * 1001}).status_code == 422


def test_documents_de_l_employe_sans_confidentiels(services):
    ids = {d["doc_id"] for d in client.get("/documents", headers=connexion("employe")).json()["documents"]}
    assert "RHC-001" not in ids and "RH-001" in ids


def test_documents_de_rh_avec_la_grille(services):
    ids = {d["doc_id"] for d in client.get("/documents", headers=connexion("rh")).json()["documents"]}
    assert "RHC-001" in ids


def test_ask_employe_ne_voit_pas_les_salaires(services):
    r = client.post("/ask", headers=connexion("employe"),
                    json={"question": "Quels sont les niveaux de salaires ?"}).json()
    assert not any(s["doc_id"].startswith("RHC-") for s in r["sources"])
    assert "2 000" not in r["reponse"]


def test_ask_rh_obtient_la_grille_avec_sa_source(services):
    r = client.post("/ask", headers=connexion("rh"),
                    json={"question": "Quels sont les niveaux de salaires ?"}).json()
    assert any(s["doc_id"] == "RHC-001" for s in r["sources"])