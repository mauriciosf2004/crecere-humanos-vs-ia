"""Comprueba por máquina que cada positivo del modelo está anclado en el texto.

La rúbrica obliga a citar literalmente la frase que justifica cada respuesta
afirmativa. Eso vuelve verificable, sin escuchar, una parte de la validación: si la
cita no aparece en la transcripción que vio el modelo, el positivo no está respaldado.

Anclada no significa correcta —una cita literal puede estar mal interpretada—, pero
descarta la invención, que es el modo de fallo que más daño haría. No sustituye
escuchar: dice dónde hay que escuchar.

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


def _quotes(row: dict, name: str) -> list[str]:
    value = row.get(name)
    if not isinstance(value, dict):
        return []
    return [text for key, text in value.items() if key.startswith("quote") and text]


def audit() -> dict:
    """Conteos por variable y por brazo: positivos, con cita, y con cita anclada."""
    counts = {
        name: {arm: {"positivos": 0, "con_cita": 0, "anclados": 0} for arm in ARMS}
        for name, _, _ in FAMILY
    }
    for arm in ARMS:
        for path in sorted((EXTRACTIONS / arm).glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            segments = json.loads((TRANSCRIPTS / arm / path.name).read_text(encoding="utf-8"))
            transcript = clean(segments.get("transcription", []))
            for name, _, _ in FAMILY:
                if not cell(row, name):
                    continue
                bucket = counts[name][arm]
                bucket["positivos"] += 1
                quotes = _quotes(row, name)
                if not quotes:
                    continue
                bucket["con_cita"] += 1
                if all(is_anchored(q, transcript) for q in quotes):
                    bucket["anclados"] += 1

    def total(select) -> dict:
        keys = ("positivos", "con_cita", "anclados")
        return {k: sum(select(name)[k] for name, _, _ in FAMILY) for k in keys}

    return {
        "por_variable": counts,
        "por_brazo": {arm: total(lambda name, a=arm: counts[name][a]) for arm in ARMS},
        "total": {
            k: sum(counts[name][arm][k] for name, _, _ in FAMILY for arm in ARMS)
            for k in ("positivos", "con_cita", "anclados")
        },
    }


def main() -> None:
    result = audit()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "anchoring.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    t = result["total"]
    print(f"Positivos {t['positivos']} · con cita {t['con_cita']} · anclados {t['anclados']}")
    for arm, b in result["por_brazo"].items():
        print(f"  {arm:<7} {b['anclados']}/{b['positivos']} positivos anclados")


if __name__ == "__main__":
    main()
