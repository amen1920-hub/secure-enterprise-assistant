from rag import retrieve_scored

DANS_LE_DOMAINE = [
    "Combien de jours de congés payés par an ?",
    "Quelle est la politique de télétravail ?",
    "Quelle est la longueur minimale d'un mot de passe ?",
    "Comment rembourser mes frais de mission ?",
    "Quelle est la durée de la période d'essai ?",
]
HORS_SUJET = [
    "Quelle est la capitale de la France ?",
    "Qui a gagné la coupe du monde 2018 ?",
    "Donne-moi une recette de couscous",
    "Comment fonctionne un moteur à explosion ?",
    "Quel temps fait-il à Paris ?",
]

for titre, questions in (("DANS LE DOMAINE", DANS_LE_DOMAINE), ("HORS SUJET", HORS_SUJET)):
    print(f"\n== {titre} ==")
    for q in questions:
        doc, score = retrieve_scored(q, "admin", k=1)[0]
        print(f"{score:.3f}  {doc.metadata['doc_id']:10}  {q}")