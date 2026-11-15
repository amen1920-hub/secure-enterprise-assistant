import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent
for dossier in ("api", "rag", "agent"):
    sys.path.insert(0, str(ROOT / dossier))

import auth  # noqa: E402

app = FastAPI(title="SecureDocs AI", version="1.0")

origines = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origines],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

schema = HTTPBearer(auto_error=False)
ENTETE_401 = {"WWW-Authenticate": "Bearer"}


class Identifiants(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class Question(BaseModel):
    # extra="forbid" : un champ "role" dans le corps est rejeté (erreur 422).
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)


def utilisateur_courant(creds: HTTPAuthorizationCredentials = Depends(schema)):
    """Le rôle vient uniquement du jeton signé, jamais de la requête."""
    if creds is None:
        raise HTTPException(401, "Authentification requise.", headers=ENTETE_401)
    try:
        return auth.verifier_jeton(creds.credentials)
    except ValueError:
        raise HTTPException(401, "Jeton invalide ou expiré.", headers=ENTETE_401)


@app.get("/health")
def health():
    return {"statut": "ok"}


@app.post("/login")
def login(identifiants: Identifiants):
    utilisateur = auth.authentifier(identifiants.email, identifiants.password)
    if utilisateur is None:
        raise HTTPException(401, "Email ou mot de passe incorrect.", headers=ENTETE_401)
    return {
        "access_token": auth.creer_jeton(utilisateur),
        "token_type": "bearer",
        "email": utilisateur["email"],
        "role": utilisateur["role"],
    }


@app.get("/me")
def me(utilisateur=Depends(utilisateur_courant)):
    return utilisateur


@app.get("/documents")
def documents(utilisateur=Depends(utilisateur_courant)):
    import tools
    return tools.get_user_permissions(utilisateur["role"])


@app.post("/ask")
def ask(corps: Question, utilisateur=Depends(utilisateur_courant)):
    import graph
    return graph.ask(corps.question, utilisateur["role"])