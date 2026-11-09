from rag import answer

print("Assistant NovaTech (tape 'quit' pour sortir)\n")
while True:
    question = input("Vous : ").strip()
    if question.lower() in ("quit", "exit", "q"):
        break
    if not question:
        continue
    resultat = answer(question)
    print(f"\nAssistant : {resultat['reponse']}")
    for s in resultat["sources"]:
        print(f"   [{s['n']}] {s['doc_id']} v{s['version']} - {s['titre']} - {s['section']}")
    print(f"   (score : {resultat['score']:.3f})\n")