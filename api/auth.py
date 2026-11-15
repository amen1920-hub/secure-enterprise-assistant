import json
import os
import time
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

USERS_FILE = ROOT / "data" / "users.json"
ROLES = ["employe", "manager", "rh", "finance", "admin"]
ALGORITHME = "HS256"
DUREE_PAR_DEFAUT = 3600  # une heure

# Hash factice : on fait le même calcul même si l'email n'existe pas,
# pour ne pas révéler quels comptes existent par le temps de réponse.
_FAUX_HASH = bcrypt.hashpw(b"x", bcrypt.gensalt()).decode()


def _secret():
    s = os.getenv("JWT_SECRET", "")
    if len(s) < 32:
        raise RuntimeError("JWT_SECRET absent ou trop court (32 caractères minimum) dans .env")
    return s


def charger_utilisateurs():
    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return {u["email"]: u for u in data}


def authentifier(email, mot_de_passe):
    """Renvoie l'utilisateur si les identifiants sont corrects, sinon None."""
    utilisateur = charger_utilisateurs().get((email or "").strip().lower())
    hash_ = utilisateur["password_hash"] if utilisateur else _FAUX_HASH
    correct = bcrypt.checkpw((mot_de_passe or "").encode(), hash_.encode())
    return utilisateur if (utilisateur and correct) else None


def creer_jeton(utilisateur, duree=DUREE_PAR_DEFAUT):
    maintenant = int(time.time())
    charge = {"sub": utilisateur["email"], "role": utilisateur["role"],
              "iat": maintenant, "exp": maintenant + duree}
    return jwt.encode(charge, _secret(), algorithm=ALGORITHME)


def verifier_jeton(jeton):
    """Renvoie {'email', 'role'} si le jeton est valide, sinon lève ValueError."""
    try:
        charge = jwt.decode(jeton, _secret(), algorithms=[ALGORITHME])
    except jwt.PyJWTError as e:
        raise ValueError(f"Jeton invalide : {e}")
    if charge.get("role") not in ROLES:
        raise ValueError("Rôle inconnu dans le jeton.")
    return {"email": charge["sub"], "role": charge["role"]}