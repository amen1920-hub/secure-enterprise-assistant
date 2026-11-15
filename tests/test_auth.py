import time

import jwt
import pytest

import auth


def test_connexion_correcte_renvoie_le_bon_role():
    u = auth.authentifier("rh@novatech.tn", "rh-demo-2026")
    assert u is not None and u["role"] == "rh"


def test_mauvais_mot_de_passe_est_refuse():
    assert auth.authentifier("rh@novatech.tn", "mauvais") is None


def test_email_inconnu_est_refuse():
    assert auth.authentifier("pirate@novatech.tn", "rh-demo-2026") is None


def test_le_jeton_porte_le_role_du_compte():
    u = auth.authentifier("employe@novatech.tn", "employe-demo-2026")
    info = auth.verifier_jeton(auth.creer_jeton(u))
    assert info == {"email": "employe@novatech.tn", "role": "employe"}


def test_jeton_modifie_est_refuse():
    u = auth.authentifier("employe@novatech.tn", "employe-demo-2026")
    jeton = auth.creer_jeton(u)
    faux = jwt.encode({"sub": u["email"], "role": "admin", "exp": int(time.time()) + 3600},
                      "une-autre-cle-secrete-de-plus-de-32-caracteres", algorithm="HS256")
    for candidat in (faux, jeton[:-3] + "xxx"):
        with pytest.raises(ValueError):
            auth.verifier_jeton(candidat)


def test_jeton_expire_est_refuse():
    u = auth.authentifier("rh@novatech.tn", "rh-demo-2026")
    with pytest.raises(ValueError):
        auth.verifier_jeton(auth.creer_jeton(u, duree=-10))


def test_jeton_avec_un_role_inconnu_est_refuse():
    u = {"email": "x@novatech.tn", "role": "pirate"}
    with pytest.raises(ValueError):
        auth.verifier_jeton(auth.creer_jeton(u))


def test_aucun_mot_de_passe_en_clair_dans_users_json():
    contenu = auth.USERS_FILE.read_text(encoding="utf-8")
    assert "demo-2026" not in contenu