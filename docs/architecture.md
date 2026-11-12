# Architecture

## Schéma général

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
        __start__([<p>__start__</p>]):::first
        verifier_role(verifier_role)
        rechercher(rechercher)
        refuser_hors_sujet(refuser_hors_sujet)
        generer(generer)
        verifier_citations(verifier_citations)
        __end__([<p>__end__</p>]):::last
        __start__ --> verifier_role;
        generer --> verifier_citations;
        rechercher -.-> generer;
        rechercher -. &nbsp;refuser&nbsp; .-> refuser_hors_sujet;
        verifier_role -. &nbsp;stop&nbsp; .-> __end__;
        verifier_role -. &nbsp;suite&nbsp; .-> rechercher;
        refuser_hors_sujet --> __end__;
        verifier_citations --> __end__;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc
```

## Flux d'une question

1. L'utilisateur se connecte et pose une question.
2. L'API identifie son rôle grâce au jeton JWT.
3. L'agent LangGraph vérifie les permissions de ce rôle.
4. La recherche ne porte que sur les documents autorisés (filtre appliqué avant la récupération).
5. Les passages trouvés sont reclassés par le reranker.
6. Le LLM répond uniquement à partir de ces passages et cite ses sources.
7. Si aucun document autorisé ne répond, l'assistant refuse ou dit qu'il ne sait pas.

## Pipeline d'ingestion

Documents (PDF, DOCX, MD) → extraction du texte → découpage en chunks → métadonnées (département, confidentialité, rôles, version, date) → embeddings `bge-m3` → Qdrant.