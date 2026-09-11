"""Inventario técnico del corpus de audio.

Primer paso del pipeline y el único que corre sin transcribir nada. Responde tres
preguntas que condicionan todo el análisis posterior:

1. ¿El formato difiere entre brazos? Si humanos e IA vinieran de cadenas de grabación
   distintas, las métricas acústicas medirían el instrumento y no la conducta.
2. ¿Cuántas llamadas son inutilizables (buzón, cuelgue)? Define el n analizable.
3. ¿Cuánto dura el corpus? Acota el costo de la transcripción antes de lanzarla.

Escribe dos tablas por política de PII:
  data/interim/inventory.csv  incluye el nombre de archivo  -> no se versiona
  data/public/durations.csv   id hasheado + brazo + duración -> se versiona
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PUBLIC = ROOT / "data" / "public"

ARMS = {"humano": "human", "ia": "ai"}


@dataclass(frozen=True)
class Track:
    """Una grabación con sus propiedades técnicas."""

    arm: str
    filename: str
    codec: str
    sample_rate: int
    channels: int
    duration_s: float

    @property
    def call_id(self) -> str:
        """Identificador estable y desidentificado, derivado del nombre del archivo."""
        return hashlib.sha256(self.filename.encode()).hexdigest()[:12]


def probe(path: Path, arm: str) -> Track:
    """Lee las propiedades del stream de audio con ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    return Track(
        arm=arm,
        filename=path.name,
        codec=stream["codec_name"],
        sample_rate=int(stream["sample_rate"]),
        channels=int(stream["channels"]),
        duration_s=float(payload["format"]["duration"]),
    )


def collect() -> list[Track]:
    """Recorre data/raw/<brazo>/ y devuelve un Track por archivo."""
    tracks = [probe(path, arm) for arm in ARMS for path in sorted((RAW / arm).glob("*.wav"))]
    if not tracks:
        raise FileNotFoundError(f"No hay audios en {RAW}. ¿Se movieron los originales?")
    return tracks


def write_tables(tracks: list[Track]) -> None:
    """Escribe la tabla interna (con nombres) y la pública (desidentificada)."""
    INTERIM.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)

    with (INTERIM / "inventory.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(tracks[0])))
        writer.writeheader()
        writer.writerows(asdict(t) for t in tracks)

    with (PUBLIC / "durations.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["call_id", "arm", "duration_s"])
        writer.writerows([t.call_id, t.arm, round(t.duration_s, 1)] for t in tracks)


def summarise(tracks: list[Track]) -> str:
    """Resumen legible: la tabla formato x brazo es la que decide el plan."""
    lines: list[str] = []
    formats = {(t.arm, t.codec, t.sample_rate, t.channels) for t in tracks}
    lines.append("Formato x brazo")
    for arm, codec, rate, channels in sorted(formats):
        n = sum(1 for t in tracks if t.arm == arm and t.codec == codec)
        layout = "mono" if channels == 1 else f"{channels}ch"
        lines.append(f"  {arm:<7} {codec} · {rate} Hz · {layout} · n={n}")

    lines.append("")
    lines.append("Duración")
    for arm in ARMS:
        durations = sorted(t.duration_s for t in tracks if t.arm == arm)
        median = statistics.median(durations)  # promedia los dos centrales si n es par
        lines.append(
            f"  {arm:<7} n={len(durations):<4} mediana={median:6.1f}s  "
            f"total={sum(durations) / 60:6.1f} min  "
            f"min={durations[0]:.0f}s  max={durations[-1]:.0f}s"
        )

    short = sum(1 for t in tracks if t.duration_s < 20)
    lines.append("")
    lines.append(f"Llamadas < 20 s (posible buzón o cuelgue): {short}")
    lines.append(f"Corpus total: {sum(t.duration_s for t in tracks) / 3600:.1f} h")
    return "\n".join(lines)


def main() -> None:
    tracks = collect()
    write_tables(tracks)
    print(summarise(tracks))


if __name__ == "__main__":
    main()
