"""Comprueba por máquina que cada positivo está anclado en el texto que se anotó.

La rúbrica obliga a citar literalmente la frase que justifica cada respuesta
afirmativa. Eso vuelve verificable, sin escuchar, una parte de la validación: si la
cita no aparece en la transcripción que vio el anotador, el positivo no está respaldado.

Anclada no significa correcta —una cita literal puede estar mal interpretada—, pero
descarta la invención, que es el modo de fallo que más daño haría.

Las citas se buscan solo en lo que el anotador tuvo delante: la extracción original
vio una transcripción; el panel, las dos cuando existen. Buscar en más texto del que
vio inflaría el anclaje.

Se anclan las ocho variables de la familia y también las dos de contexto, porque el
argumento de que los brazos no son comparables descansa entero sobre ellas.

Escribe data/public/anchoring.json con conteos, sin una palabra de las citas.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from src.analyze import CONSENSUS, EXTRACTIONS, FAMILY, cell
from src.extract import clean

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "data" / "interim" / "transcripts"
SECOND = ROOT / "data" / "interim" / "transcripts_large-v3"
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


def _seen(arm: str, stem: str, source: Path) -> list[str]:
    """Las transcripciones que tuvo delante quien anotó esta fuente."""
    texts = [
        clean(
            json.loads((TRANSCRIPTS / arm / f"{stem}.json").read_text(encoding="utf-8"))[
                "transcription"
            ]
        )
    ]
    second = SECOND / arm / f"{stem}.json"
    if source == CONSENSUS and second.exists():
        texts.append(clean(json.loads(second.read_text(encoding="utf-8"))["transcription"]))
    return texts


def _sum(counts: dict, names: list[str], arms: tuple[str, ...] = ARMS) -> dict:
    return {k: sum(counts[name][arm][k] for name in names for arm in arms) for k in COUNTS}


def audit(source: Path = EXTRACTIONS) -> dict:
    """Conteos por variable y por brazo: positivos, con cita, y con cita anclada."""
    names = FAMILY_NAMES + list(CONTEXT_POSITIVE)
    counts = {name: {arm: dict.fromkeys(COUNTS, 0) for arm in ARMS} for name in names}
    for arm in ARMS:
        for path in sorted((source / arm).glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            texts = _seen(arm, path.stem, source)
            for name in names:
                if not _is_positive(row, name):
                    continue
                bucket = counts[name][arm]
                bucket["positivos"] += 1
                quotes = _quotes(row, name)
                if not quotes:
                    continue
                bucket["con_cita"] += 1
                if all(any(is_anchored(q, text) for text in texts) for q in quotes):
                    bucket["anclados"] += 1

    return {
        "fuente": source.name,
        "por_variable": counts,
        "por_brazo": {arm: _sum(counts, FAMILY_NAMES, (arm,)) for arm in ARMS},
        "total": _sum(counts, FAMILY_NAMES),
        "total_contexto": _sum(counts, list(CONTEXT_POSITIVE)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Anclaje de citas en las transcripciones.")
    parser.add_argument("--source", choices=("extraccion", "consenso"), default="consenso")
    source = CONSENSUS if parser.parse_args().source == "consenso" else EXTRACTIONS

    result = audit(source)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "anchoring.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for title, key in (("Familia", "total"), ("Contexto", "total_contexto")):
        t = result[key]
        print(
            f"{title} ({result['fuente']}): positivos {t['positivos']} · anclados {t['anclados']}"
        )


if __name__ == "__main__":
    main()
