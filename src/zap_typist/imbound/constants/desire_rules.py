"""Seed inicial da settings key `desire_rules`.

Cada regra e um dict {"pattern": str, "transform": str} onde:
- `pattern` e regex case-insensitive (compilado em runtime pelo DesireAdapter)
- `transform` e template com `{desire}` interpolado pelo DesireAdapter

A ultima regra (pattern `.*`) DEVE ser sempre o catch-all default.
"""

DESIRE_RULES_SEED: list[dict[str, str]] = [
    {"pattern": r"nuvemshop|loja\s+nuvem", "transform": "criar uma loja Nuvemshop"},
    {"pattern": r"^criar\s+", "transform": "{desire}"},
    {"pattern": r"^fazer\s+", "transform": "{desire}"},
    {"pattern": r"^desenvolver\s+", "transform": "{desire}"},
    {"pattern": r".*", "transform": "o desenvolvimento de {desire}"},
]
