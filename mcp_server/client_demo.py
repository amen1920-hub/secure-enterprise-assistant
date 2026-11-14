import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "server.py"
QUESTION = "Quels sont les niveaux de salaires ?"


async def appeler(session, nom, arguments=None):
    r = await session.call_tool(nom, arguments or {})
    return json.loads(r.content[0].text)


async def demo(role):
    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)],
        env={**os.environ, "MCP_USER_ROLE": role})
    async with stdio_client(params) as (lecture, ecriture):
        async with ClientSession(lecture, ecriture) as session:
            await session.initialize()
            outils = [t.name for t in (await session.list_tools()).tools]
            print(f"\n=== Utilisateur : {role} ===")
            print("Outils découverts :", ", ".join(outils))

            perms = await appeler(session, "get_user_permissions")
            print(f"Documents accessibles : {perms['nombre']}")

            recherche = await appeler(session, "search_documents", {"question": QUESTION})
            ids = sorted({p["doc_id"] for p in recherche["passages"]})
            print(f"Recherche « {QUESTION} » -> documents : {ids or 'aucun'}")

            meta = await appeler(session, "get_document_metadata", {"doc_id": "RHC-001"})
            print("Métadonnées de RHC-001 ->", meta)


async def main():
    for role in ("employe", "rh"):
        await demo(role)


if __name__ == "__main__":
    asyncio.run(main())