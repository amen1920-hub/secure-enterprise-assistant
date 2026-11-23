from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def modele():
    try:
        import router_model
        router_model._charger()
        router_model._emb.embed_query("test")
    except Exception as e:
        pytest.skip(f"Modèle de routage ou Ollama indisponible : {e}")
    return router_model


def test_questions_de_contenu_vont_a_la_recherche(modele):
    for q in ("combien department il ya",
              "je veux consulter politique de travail",
              "Quelle est la politique d'accès au VPN ?",
              "Quel est le salaire minimum chez NovaTech ?"):
        assert modele.decider(q)[0] == "recherche", q


def test_liste_des_acces(modele):
    assert modele.decider("Quels documents puis-je consulter ?")[0] == "permissions"


def test_infos_d_un_document_avec_identifiant(modele):
    route, doc_id, _ = modele.decider("Donne-moi les informations du document RHC-001")
    assert route == "metadonnees" and doc_id == "RHC-001"


def test_metadonnees_sans_identifiant_valide_est_impossible(modele):
    assert modele.decider("Donne-moi la version du document")[0] != "metadonnees"


def test_repli_sur_la_recherche_si_le_modele_est_absent(modele, monkeypatch):
    monkeypatch.setattr(modele, "MODELE", Path("modele_inexistant.joblib"))
    monkeypatch.setattr(modele, "_clf", None)
    assert modele.decider("Quels documents puis-je consulter ?") == ("recherche", "", 0.0)
    
def test_resume_avec_identifiant(modele):
    route, doc_id, _ = modele.decider("Résume le document IT-001")
    assert route == "document" and doc_id == "IT-001"


def test_resume_sans_identifiant_demande_une_precision(modele):
    assert modele.decider("résumer du contenu")[0] == "precision"