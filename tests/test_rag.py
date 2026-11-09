import re
import pytest

QUESTIONS_DOMAINE = [
    "Combien de jours de congés payés par an ?",
    "Quelle est la politique de télétravail ?",
    "Quelle est la longueur minimale d'un mot de passe ?",
    "Comment rembourser mes frais de mission ?",
]
HORS_SUJET = [
    "Quelle est la capitale de la France ?",
    "Qui a gagné la coupe du monde 2018 ?",
    "Donne-moi une recette de couscous",
]


@pytest.fixture(scope="module")
def rag():
    try:
        import rag as module
        module.client.get_collections()
    except Exception as e:
        pytest.skip(f"Qdrant ou Ollama indisponible : {e}")
    return module


def test_reponse_correcte_avec_citation(rag):
    r = rag.answer("Combien de jours de congés payés par an ?")
    assert "25" in r["reponse"]
    assert any(s["doc_id"] == "RH-001" for s in r["sources"])


@pytest.mark.parametrize("question", HORS_SUJET)
def test_hors_sujet_est_refuse(rag, question):
    r = rag.answer(question)
    assert r["reponse"] == rag.REFUS
    assert r["sources"] == []


@pytest.mark.parametrize("question", QUESTIONS_DOMAINE)
def test_aucune_version_obsolete_dans_les_sources(rag, question):
    r = rag.answer(question)
    for s in r["sources"]:
        assert not s["doc_id"].endswith("-V1"), s


@pytest.mark.parametrize("question", QUESTIONS_DOMAINE)
def test_les_sources_sont_citees_dans_la_reponse(rag, question):
    r = rag.answer(question)
    cites = {int(n) for n in re.findall(r"\[(\d+)\]", r["reponse"])}
    assert {s["n"] for s in r["sources"]} <= cites


def test_seuil_separe_domaine_et_hors_sujet(rag):
    for q in QUESTIONS_DOMAINE:
        assert rag.retrieve_scored(q, k=1)[0][1] >= rag.SEUIL, q
    for q in HORS_SUJET:
        assert rag.retrieve_scored(q, k=1)[0][1] < rag.SEUIL, q