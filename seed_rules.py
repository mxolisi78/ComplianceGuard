import json
from pathlib import Path
from src.rules_store import add_rules, count, reset

reset()

rules = json.loads(Path("data/rules/rules.json").read_text(encoding="utf-8-sig"))
n = add_rules(rules)
print(f"Added {n} rules. Total: {count()}")
