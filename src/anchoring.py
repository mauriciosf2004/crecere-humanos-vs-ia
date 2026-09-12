"""Comprueba por máquina que cada positivo del modelo está anclado en el texto.

La rúbrica obliga a citar literalmente la frase que justifica cada respuesta
afirmativa. Eso vuelve verificable, sin escuchar, una parte de la validación: si la
cita no aparece en la transcripción que vio el modelo, el positivo no está respaldado.

Anclada no significa correcta —una cita literal puede estar mal interpretada—, pero
descarta la invención, que es el modo de fallo que más daño haría. No sustituye
escuchar: dice dónde hay que escuchar.

Se anclan las ocho variables de la familia y también las dos de contexto, porque el
argumento de que los brazos no son comparables descansa entero sobre ellas.

Escribe data/public/anchoring.json con conteos, sin una palabra de las citas.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from src.analyze import FAMILY, cell
from src.extract import clean

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "data" / "interim" / "transcripts"
EXTRACTIONS = ROOT / "data" / "interim" / "extractions"
PUBLIC = ROOT / "data" / "public"

ARMS = ("humano", "ia")
ELLIPSIS = re.compile(r"\.\.\.|…")
MIN_WORDS = 3  # un fragmento más corto coincide por azar

# Qué cuenta como positivo en las variables de contexto, que no son binarias.
CONTEXT_POSITIVE = {"prior_agreement_followup": True, "effective_contact": "titular"}
FAMILY_NAMES = [name for name, _, _ in FAMILY]
COUNTS = ("positivos", "con_cita", "anclados")


def normalize(text: str) -> str:
    """Minúsculas, sin tildes ni puntuación, con los espacios colapsados."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", plain)).strip()


def is_anchored(quote: str, transcript: str) -> bool:
    """¿Aparece la cita, fragmento a fragmento y con palabras completas, en el texto?

    El modelo a veces une dos trozos con puntos suspensivos: cada trozo debe estar.
    """
    haystack = f" {normalize(transcript)} "
    fragments = [normalize(part) for part in ELLIPSIS.split(quote)]
    meaningful = [f for f in fragments if len(f.split()) >= MIN_WORDS] or [
        f for f in fragments if f
    ]
    return bool(meaningful) and all(f" {f} " in haystack for f in meaningful)


def _is_positive(row: dict, name: str) -> bool:
    if name in CONTEXT_POSITIVE:
        value = row.get(name)
        raw = value.get("value") if isinstance(value, dict) else value
        return raw == CONTEXT_POSITIVE[name]
    return bool(cell(row, name))


def _quotes(row: dict, name: str) -> list[str]:
    value = row.get(name)
    if not isinstance(value, dict):
        return []
    return [text for key, text in value.items() if key.startswith("quote") and text]


def _sum(counts: dict, names: list[str], arms: tuple[str, ...] = ARMS) -> dict:
    return {k: sum(counts[name][arm][k] for name in names for arm in arms) for k in COUNTS}


def audit() -> dict:
    """Conteos por variable y por brazo: positivos, con cita, y con cita anclada."""
    names = FAMILY_NAMES + list(CONTEXT_POSITIVE)
    counts = {name: {arm: dict.fromkeys(COUNTS, 0) for arm in ARMS} for name in names}
    for arm in ARMS:
        for path in sorted((EXTRACTIONS / arm).glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            segments = json.loads((TRANSCRIPTS / arm / path.name).read_text(encoding="utf-8"))
            transcript = clean(segments.get("transcription", []))
            for name in names:
                if not _is_positive(row, name):
                    continue
                bucket = counts[name][arm]
                bucket["positivos"] += 1
                quotes = _quotes(row, name)
                if not quotes:
                    continue
                bucket["con_cita"] += 1
                if all(is_anchored(q, transcript) for q in quotes):
                    bucket["anclados"] += 1

    return {
        "por_variable": counts,
        "por_brazo": {arm: _sum(counts, FAMILY_NAMES, (arm,)) for arm in ARMS},
        "total": _sum(counts, FAMILY_NAMES),
        "total_contexto": _sum(counts, list(CONTEXT_POSITIVE)),
    }


def main() -> None:
    result = audit()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "anchoring.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for title, key in (("Familia", "total"), ("Contexto", "total_contexto")):
        t = result[key]
        print(
            f"{title}: positivos {t['positivos']} · con cita {t['con_cita']} · anclados "
            f"{t['anclados']}"
        )


if __name__ == "__main__":
    main()
