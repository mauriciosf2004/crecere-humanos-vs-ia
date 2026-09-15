"""Convierte cada transcripción en una fila de datos aplicando src/rubric.md.

El motor es `claude -p` en modo headless: usa la suscripción, no necesita clave de
API, y no sale de la máquina más que el texto ya transcrito. La salida se valida
contra src/schema.json en el propio CLI, así que una respuesta mal formada se
rechaza antes de llegar aquí.

Es idempotente: cachea por hash del texto de entrada más la versión de la rúbrica,
de modo que cambiar la rúbrica invalida la caché y volver a correr no repite trabajo
ya hecho. El call_id no se le pregunta al modelo —devolvía un marcador de posición—
sino que se deriva del nombre del archivo, igual que en el inventario.

Es la pasada histórica de un solo modelo: el análisis usa el consenso del panel
(src/annotate.py), que de aquí solo toma citas para la regla literal de fecha.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "data" / "interim" / "transcripts"
CACHE = ROOT / "data" / "interim" / "extractions"
RUBRIC = ROOT / "src" / "rubric.md"
SCHEMA = ROOT / "src" / "schema.json"

ARMS = ("humano", "ia")
WORKERS = 6
MODEL = "claude-sonnet-5"

# Alucinaciones canónicas de whisper en los silencios: texto de YouTube que no puede
# aparecer en una llamada de cobranza. Son diferenciales por brazo (14/50 humano vs
# 1/50 IA), así que se eliminan antes de que el modelo las lea.
HALLUCINATION = re.compile(
    r"suscr[ií]b\w*\s+al\s+canal|gracias por ver (el|este) v[ií]deo|"
    r"subt[ií]tulos (realizados|creados|por la comunidad)|amara\.org|"
    r"m[áa]s v[ií]deos|no olvides suscribirte",
    re.I,
)


def call_id(stem: str) -> str:
    """Mismo identificador desidentificado que usa el inventario."""
    return hashlib.sha256(f"{stem}.wav".encode()).hexdigest()[:12]


def clean(segments: list[dict]) -> str:
    """Texto plano de la llamada, sin alucinaciones ni bucles del decodificador."""
    lines: list[str] = []
    for segment in segments:
        text = segment["text"].strip()
        if not text or HALLUCINATION.search(text):
            continue
        # un bucle del decodificador repite el mismo segmento; basta con la primera vez
        if lines and text == lines[-1]:
            continue
        lines.append(text)
    return "\n".join(lines)


def ask(
    text: str,
    rubric: str,
    schema: str,
    turns: int,
    model: str = MODEL,
    effort: str | None = None,
) -> dict | None:
    """Una invocación del CLI. Devuelve la fila validada, o None ante cualquier fallo.

    El texto va por stdin y no como argumento posicional: hay transcripciones que
    empiezan por guion ("-Aló.") y el CLI las interpretaba como una opción
    desconocida, fallando con stdout vacío.

    `effort` fija el nivel de esfuerzo de esta llamada. Sin él, el CLI hereda el de la
    configuración del usuario, y no todos los modelos aceptan cualquier nivel: Opus
    rechaza "xhigh" con un error 400.

    Nada de lo que devuelve el subproceso se da por bueno: puede salir con error,
    escribir algo que no es JSON, o terminar por agotar turnos sin haber llamado a
    la herramienta de salida estructurada. Los tres casos se tratan igual.
    """
    command = [
        "claude",
        "-p",
        "--safe-mode",
        "--tools",
        "",
        "--model",
        model,
        "--system-prompt",
        rubric,
        "--json-schema",
        schema,
        "--output-format",
        "json",
        "--max-turns",
        str(turns),
    ]
    if effort:
        command += ["--effort", effort]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "MAX_THINKING_TOKENS": "0",
            },  # sin razonamiento: baja coste y dispersión
            input=text,  # por stdin: ver la nota del docstring
            timeout=300,
        )
        payload = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None

    if payload.get("is_error"):
        return None

    row = payload.get("result")
    if isinstance(row, str):
        try:
            row = json.loads(row)
        except json.JSONDecodeError:
            return None
    if not isinstance(row, dict):
        return None

    row["_cost_usd"] = payload.get("total_cost_usd")
    # un alias como "opus" resuelve al modelo vigente: se guarda a cuál resolvió
    row["_models"] = sorted(payload.get("modelUsage") or {})
    return row


def extract(path: Path, arm: str, rubric: str, schema: str) -> dict | None:
    """Una llamada al modelo por transcripción. Devuelve la fila, o None si falló."""
    segments = json.loads(path.read_text(encoding="utf-8")).get("transcription", [])
    text = clean(segments)
    fingerprint = hashlib.sha256(f"{rubric}\n{text}".encode()).hexdigest()[:16]
    cached = CACHE / arm / f"{path.stem}.json"

    if cached.exists():
        previous = json.loads(cached.read_text(encoding="utf-8"))
        if previous.get("_fingerprint") == fingerprint:
            return previous

    row = ask(text, rubric, schema, turns=8)
    if row is None:
        row = ask(text, rubric, schema, turns=16)  # un reintento: algunas agotan turnos
    if row is None:
        return None

    row["call_id"] = call_id(path.stem)  # no se le pregunta al modelo
    row["arm"] = arm
    row["_fingerprint"] = fingerprint

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def main() -> None:
    rubric = RUBRIC.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    jobs = [(path, arm) for arm in ARMS for path in sorted((TRANSCRIPTS / arm).glob("*.json"))]
    if not jobs:
        raise SystemExit(
            "No hay transcripciones en data/interim/transcripts/: corre `make transcribe`, "
            "que necesita los audios de data/raw/."
        )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(lambda job: extract(job[0], job[1], rubric, schema), jobs))

    ok = [r for r in rows if r]
    cost = sum(r.get("_cost_usd") or 0 for r in ok)
    print(f"Extraídas {len(ok)}/{len(jobs)} · fallidas {len(jobs) - len(ok)} · coste ${cost:.2f}")


if __name__ == "__main__":
    main()
