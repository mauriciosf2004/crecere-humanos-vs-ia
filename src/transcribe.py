"""Transcribe el corpus con whisper.cpp, en local.

Ningún audio sale del equipo: son grabaciones de deudores reales y subirlas a un
servicio de terceros exigiría un acuerdo de tratamiento de datos que no existe.

Decisiones de configuración, todas medidas y no heredadas:
  large-v3-turbo   2,6x más rápido que large-v3 sin razón para pagar la diferencia
  sin -nt          -nt no es cosmético: colapsa la decodificación en bloques de 30 s
                   y pierde ~23% de las palabras. Sin él salen los segmentos reales
                   con sus offsets, que son la base de las métricas libres de rol.
  -l es            el autodetector se equivoca en audio telefónico de 8 kHz
  -bs 5 -bo 5      beam search; el greedy alucina más en silencios
  sin --prompt     un prompt de dominio es una vía conocida de texto alucinado

Salida: un JSON por llamada en data/interim/transcripts/, cacheado. Re-ejecutar
no vuelve a transcribir lo ya hecho.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim" / "transcripts"
MODEL = Path.home() / ".whisper-models" / "ggml-large-v3-turbo.bin"

ARMS = ("humano", "ia")


def transcribe(audio: Path, arm: str) -> bool:
    """Transcribe un archivo si no está ya en caché. Devuelve True si hizo trabajo."""
    target = OUT / arm / f"{audio.stem}.json"
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "whisper-cli",
            "-m",
            str(MODEL),
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
    if not MODEL.exists():
        sys.exit(f"Falta el modelo: {MODEL}")

    audios = [(path, arm) for arm in ARMS for path in sorted((RAW / arm).glob("*.wav"))]
    started = time.monotonic()
    done = skipped = 0

    for index, (path, arm) in enumerate(audios, start=1):
        if transcribe(path, arm):
            done += 1
        else:
            skipped += 1
        elapsed = time.monotonic() - started
        rate = elapsed / max(done, 1)
        print(
            f"[{index:3d}/{len(audios)}] {arm:<7} {path.stem[:8]} "
            f"· {elapsed / 60:5.1f} min · ~{rate * (len(audios) - index) / 60:4.1f} min restantes",
            flush=True,
        )

    total_min = (time.monotonic() - started) / 60
    print(f"\nTranscritas {done}, en caché {skipped}. Total {total_min:.1f} min.")


if __name__ == "__main__":
    main()
