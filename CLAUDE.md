# Creceré AI — Humanos vs IA en gestión de cobranza

Prueba técnica. Entrega **martes 15-sep-2026**: (1) `report/index.html`, máximo **2 páginas
impresas**, mostrable al presidente de un banco; (2) el repositorio con el código.
Se evalúa **criterio, claridad y capacidad de terminar bien**. Código que nadie pidió RESTA.

## Datos (medidos, no supuestos)
100 WAV · PCM s16le · **8 kHz · MONO** · 50 humano / 50 IA · 381 min totales.
Formato y nivel idénticos entre brazos (−19,6 dB vs −20,2 dB) → **sin confundido de instrumento**.
Ninguna llamada < 60 s → n analizable = 100, sin regla de exclusión.
Nombres UUID, **cero metadatos**: no hay campaña, fecha, resultado de CRM ni ID de agente.
Audio ya censurado en origen. Mono → **la diarización no es gratis**.

## Rutas (contrato)
| ruta | contenido | ¿se versiona? |
|---|---|---|
| `data/raw/{humano,ia}/` | audios originales | **NO** |
| `data/interim/` | transcripciones, anotaciones crudas | **NO** |
| `data/processed/` | tablas con texto de llamada | **NO** |
| `data/public/` | variables derivadas, sin texto | **SÍ** |
| `report/index.html` | entregable 1 | SÍ |

## Regla de PII
Son deudores reales. **Nada que contenga voz o texto de llamada sale de `data/`.**
`data/public/` se genera con una **whitelist de columnas**, nunca con una blacklist.
El repo es local y sin remoto. No se publica.

## Realidad estadística (calculada, no estimada)
n=50/50 con Fisher exacto, α=0,05: **MDE ≈ 29 pp**. Potencia 30→40 % = **13 %**; 30→50 % = **46 %**.
Si el denominador es RPC (n≈31/brazo), **MDE ≈ 37 pp**.
→ Los titulares se apoyan en **tamaños de efecto con IC**, no en p-valores.
→ **Una** métrica primaria declarada antes de mirar datos; el resto es **exploratorio** y se rotula.
→ Duración ya dio nulo: p=0,319, Cliff's δ=0,116. Es un hallazgo, no un fracaso.

## Reglas de trabajo
- Español (es-CO) en todo lo que ve el evaluador. Código e identificadores en inglés.
- **Prohibido inventar o redondear cifras a ojo.** Todo número del reporte sale de `results.json`.
- Ningún número se escribe a mano en el HTML.
- Escala: 100 filas. CSV, no parquet. Sin capas que no cambien el resultado.

## Hecho =
`make report` corre en un clon limpio · el PDF da exactamente 2 páginas sin contenido cortado ·
ningún audio ni transcripción en `git log` · cada afirmación del reporte tiene su número detrás.
