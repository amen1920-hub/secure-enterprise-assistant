import json
from pathlib import Path

import bcrypt

ROOT = Path(__file__).resolve().parent.parent
ROLES = ["employe", "manager", "rh", "finance", "admin"]

utilisateurs = []
for role in ROLES:
    mot_de_passe = f"{role}-demo-2026"
    utilisateurs.append({
        "email": f"{role}@novatech.tn",
        "role": role,
        "password_hash": bcrypt.hashpw(mot_de_passe.encode(), bcrypt.gensalt()).decode(),
    })

(ROOT / "data" / "users.json").write_text(
    json.dumps(utilisateurs, indent=2, ensure_ascii=False), encoding="utf-8")

print("Comptes de démonstration créés :")
for role in ROLES:
    print(f"  {role}@novatech.tn   mot de passe : {role}-demo-2026")