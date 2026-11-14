# Architecture

## Schéma général

```mermaid
flowchart TD
    U[Utilisateur avec un rôle] --> UI[Interface web React]
    UI --> API[API FastAPI + authentification JWT]
    API --> AG[Agent LangGraph]
    AG --> MCP[Serveur MCP]
    MCP --> T1[search_documents]
    MCP --> T2[get_user_permissions]
    MCP --> T3[get_document_metadata]
    T1 --> F[Filtre par rôle et par version]
    F --> DB[(Qdrant : vecteurs + métadonnées)]
    DB --> H[Recherche hybride : vectorielle + BM25, fusion RRF]
    H --> RR[Reranker, évalué au palier 8]
    RR --> LLM[LLM Ollama qwen2.5:3b]
    LLM --> R[Réponse avec citations]
    R --> UI
```

## Flux d'une question

1. L'utilisateur se connecte et pose une question.
2. L'API identifie son rôle grâce au jeton JWT.
3. L'agent LangGraph vérifie le rôle.
4. La recherche ne porte que sur les documents autorisés et en vigueur (filtre appliqué avant la récupération).
5. La recherche hybride fusionne le classement vectoriel et le classement BM25.
6. Si le meilleur score est sous le seuil, l'assistant refuse sans appeler le LLM.
7. Sinon, le LLM répond uniquement à partir des passages retrouvés et cite ses sources.
8. Une réponse sans citation est transformée en refus.

## Graphe de l'agent

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
        __start__([<p>__start__</p>]):::first
        verifier_role(verifier_role)
        router(router)
        lister_permissions(lister_permissions)
        infos_document(infos_document)
        rechercher(rechercher)
        refuser_hors_sujet(refuser_hors_sujet)
        generer(generer)
        verifier_citations(verifier_citations)
        __end__([<p>__end__</p>]):::last
        __start__ --> verifier_role;
        generer --> verifier_citations;
        rechercher -.-> generer;
        rechercher -. &nbsp;refuser&nbsp; .-> refuser_hors_sujet;
        router -. &nbsp;metadonnees&nbsp; .-> infos_document;
        router -. &nbsp;permissions&nbsp; .-> lister_permissions;
        router -. &nbsp;recherche&nbsp; .-> rechercher;
        verifier_role -. &nbsp;stop&nbsp; .-> __end__;
        verifier_role -. &nbsp;suite&nbsp; .-> router;
        infos_document --> __end__;
        lister_permissions --> __end__;
        refuser_hors_sujet --> __end__;
        verifier_citations --> __end__;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc
```

## Pipeline d'ingestion

Documents Markdown + manifeste YAML → validation des faits clés → découpage par sections → métadonnées (département, confidentialité, rôles autorisés, version, statut, empreinte) → embeddings `bge-m3` → Qdrant.

L'ingestion est incrémentale : une empreinte (hash) du contenu et des métadonnées détecte les documents ajoutés, modifiés ou supprimés, et seuls ceux-là sont réindexés.
