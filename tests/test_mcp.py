import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp_server" / "server.py"


@pytest.fixture(scope="module", autouse=True)
def services():
    try:
        import rag
        rag.client.get_collections()
        rag.store.embeddings.embed_query("test")
    except Exception as e:
        pytest.skip(f"Qdrant ou Ollama indisponible : {e}")


async def _session(role, scenario):
    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)],
        env={**os.environ, "MCP_USER_ROLE": role})
    async with stdio_client(params) as (lecture, ecriture):
        async with ClientSession(lecture, ecriture) as session:
            await session.initialize()
            return await scenario(session)


def lancer(role, scenario):
    return asyncio.run(_session(role, scenario))


async def appel(session, nom, arguments=None):
    r = await session.call_tool(nom, arguments or {})
    texte = r.content[0].text if r.content else ""
    return r.isError, (texte if r.isError else json.loads(texte))


def test_aucun_outil_n_expose_de_parametre_role():
    async def scenario(session):
        return (await session.list_tools()).tools

    for outil in lancer("employe", scenario):
        assert "role" not in outil.inputSchema.get("properties", {}), outil.name


def test_employe_ne_recoit_rien_de_confidentiel():
    async def scenario(session):
        _, perms = await appel(session, "get_user_permissions")
        _, recherche = await appel(session, "search_documents",
                                   {"question": "Quels sont les niveaux de salaires ?"})
        _, meta = await appel(session, "get_document_metadata", {"doc_id": "RHC-001"})
        return perms, recherche, meta

    perms, recherche, meta = lancer("employe", scenario)
    assert "RHC-001" not in {d["doc_id"] for d in perms["documents"]}
    assert not any(p["doc_id"].startswith("RHC-") for p in recherche["passages"])
    assert "erreur" in meta


def test_rh_accede_a_la_grille_des_salaires():
    async def scenario(session):
        _, recherche = await appel(session, "search_documents",
                                   {"question": "Quels sont les niveaux de salaires ?"})
        _, meta = await appel(session, "get_document_metadata", {"doc_id": "RHC-001"})
        return recherche, meta

    recherche, meta = lancer("rh", scenario)
    assert any(p["doc_id"] == "RHC-001" for p in recherche["passages"])
    assert meta["doc_id"] == "RHC-001"


def test_role_invalide_est_refuse_par_tous_les_outils():
    async def scenario(session):
        return [
            (await appel(session, "get_user_permissions"))[0],
            (await appel(session, "search_documents", {"question": "congés"}))[0],
            (await appel(session, "get_document_metadata", {"doc_id": "RH-001"}))[0],
        ]

    assert all(lancer("pirate", scenario))