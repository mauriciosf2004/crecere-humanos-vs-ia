"""Transcribe el corpus con whisper.cpp, en local.

Ningún audio sale del equipo: son grabaciones de deudores reales y subirlas a un
servicio de terceros exigiría un acuerdo de tratamiento de datos que no existe.

Hay dos pasadas. La principal usa large-v3-turbo. La segunda usa large-v3 completo,
unas 2,6 veces más lento, y existe para contrastar: donde los dos modelos coinciden la
transcripción es fiable, y donde difieren los anotadores reciben las dos versiones.

Decisiones de configuración, todas medidas y no heredadas:
  sin -nt          -nt no es cosmético: colapsa la decodificación en bloques de 30 s
                   y pierde ~23% de las palabras. Sin él salen los segmentos reales
                   con sus offsets.
  -l es            el autodetector se equivoca en audio telefónico de 8 kHz
  -bs 5 -bo 5      beam search; el greedy alucina más en silencios
  sin --prompt     un prompt de dominio es una vía conocida de texto alucinado

Salida: un JSON por llamada, cacheado. Re-ejecutar no repite lo ya hecho.

  python -m src.transcribe                    # large-v3-turbo -> data/interim/transcripts/
  python -m src.transcribe --model large-v3   # large-v3 -> data/interim/transcripts_large-v3/
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
MODELS = Path.home() / ".whisper-models"
PRIMARY = "large-v3-turbo"

ARMS = ("humano", "ia")


def output_dir(model: str) -> Path:
    """La pasada principal conserva su ruta original; las demás llevan el modelo en el nombre."""
    return INTERIM / ("transcripts" if model == PRIMARY else f"transcripts_{model}")


def transcribe(audio: Path, arm: str, model: Path, out: Path) -> bool:
    """Transcribe un archivo si no está ya en caché. Devuelve True si hizo trabajo."""
    target = out / arm / f"{audio.stem}.json"
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "whisper-cli",
            "-m",
            str(model),
            "-f",
            str(audio),
            "-l",
            "es",
            "-bs",
            "5",
            "-bo",
            "5",
            "-oj",
            "-np",
            "-of",
            str(target.with_suffix("")),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=PRIMARY, help="large-v3-turbo o large-v3")
    args = parser.parse_args()

    model = MODELS / f"ggml-{args.model}.bin"
    if not model.exists():
        sys.exit(f"Falta el modelo: {model}")
    out = output_dir(args.model)

    audios = [(path, arm) for arm in ARMS for path in sorted((RAW / arm).glob("*.wav"))]
    if not audios:
        sys.exit(
            "No hay audios en data/raw/{humano,ia}/: los entrega Creceré y no se "
            "versionan. Ver README, «Qué hay en el repositorio y qué no»."
        )
    started = time.monotonic()
    done = skipped = 0

    for index, (path, arm) in enumerate(audios, start=1):
        if transcribe(path, arm, model, out):
            done += 1
        else:
            skipped += 1
        elapsed = time.monotonic() - started
        rate = elapsed / max(done, 1)
        print(
            f"[{index:3d}/{len(audios)}] {args.model} {arm:<7} {path.stem[:8]} "
            f"· {elapsed / 60:5.1f} min · ~{rate * (len(audios) - index) / 60:4.1f} min restantes",
            flush=True,
        )

    total_min = (time.monotonic() - started) / 60
    print(f"\nTranscritas {done}, en caché {skipped}. Total {total_min:.1f} min.")


if __name__ == "__main__":
    main()
