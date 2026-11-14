import graph

ROLES = graph.rag.ROLES

role = ""
while role not in ROLES:
    role = input(f"Rôle ({', '.join(ROLES)}) : ").strip().lower()
print(f"\nAssistant NovaTech, connecté en tant que « {role} » (tape 'quit' pour sortir)\n")

while True:
    question = input("Vous : ").strip()
    if question.lower() in ("quit", "exit", "q"):
        break
    if not question:
        continue
    r = graph.ask(question, role)
    print(f"\nAssistant : {r['reponse']}")
    for s in r["sources"]:
        print(f"   [{s['n']}] {s['doc_id']} v{s['version']} - {s['titre']} - {s['section']}")
    print(f"   (statut : {r['statut']} | score : {r['score']:.3f})\n")