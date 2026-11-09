import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLES = {"employe", "manager", "rh", "finance", "admin"}
NIVEAUX = {"public", "restreint", "confidentiel"}


def charger():
    chemin = ROOT / "data" / "manifest.yaml"
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))["documents"]


def test_ids_uniques():
    ids = [d["id"] for d in charger()]
    assert len(ids) == len(set(ids))


def test_fichiers_existent():
    for d in charger():
        assert (ROOT / "data" / "raw" / f"{d['id']}.md").exists(), d["id"]


def test_roles_et_niveaux_valides():
    for d in charger():
        assert set(d["roles_autorises"]) <= ROLES, d["id"]
        assert d["confidentialite"] in NIVEAUX, d["id"]


def test_documents_non_publics_interdits_aux_employes():
    for d in charger():
        if d["confidentialite"] != "public":
            assert "employe" not in d["roles_autorises"], d["id"]


def test_chaque_ancienne_version_a_une_version_actuelle():
    docs = {d["id"]: d for d in charger()}
    for d in docs.values():
        if d.get("statut") == "obsolete":
            actuel = docs.get(d["famille"])
            assert actuel is not None, d["id"]
            assert actuel.get("statut", "actuelle") == "actuelle", d["id"]