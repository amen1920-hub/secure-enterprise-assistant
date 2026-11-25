from pathlib import Path

p = Path(__file__).resolve().parent.parent / "data" / "manifest.yaml"
t = p.read_text(encoding="utf-8")
n = t.lower().count("availability")
for ancien, nouveau in (("d''availability", "de disponibilité"),
                        ("d'availability", "de disponibilité"),
                        ("availability", "disponibilité"),
                        ("Availability", "Disponibilité")):
    t = t.replace(ancien, nouveau)
p.write_text(t, encoding="utf-8")
print(n, "remplacement(s)")