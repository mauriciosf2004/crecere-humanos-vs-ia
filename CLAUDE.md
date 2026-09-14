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
| `data/interim/{annotations,consensus}/` | votos del panel y su consenso | **NO** |
| `data/public/` | variables derivadas, sin texto | **SÍ** |
| `report/index.html` | entregable 1 | SÍ |

## Regla de PII
Son deudores reales. **Nada que identifique a un deudor sale de `data/`**: ni voz, ni
transcripciones, ni nombres, cédulas, teléfonos o montos de una llamada concreta. Las frases de guion
del agente pueden citarse como ejemplo.
`data/public/` se genera con una **whitelist de columnas**, nunca con una blacklist.
El repositorio se publica en GitHub porque el encargo lo exige. Antes de cada push se comprueba
que no entre nada de `data/raw`, `data/interim` ni `data/processed`.

## Realidad estadística (calculada, no estimada)
n=50/50 con Fisher exacto, α=0,05: **MDE ≈ 29 pp**. Potencia 30→40 % = **13 %**; 30→50 % = **46 %**.
Si el denominador es RPC (n≈31/brazo), **MDE ≈ 37 pp**.
→ Los titulares se apoyan en **tamaños de efecto con IC**, no en p-valores.
→ Inferencia en dos niveles: test global por permutación como compuerta, y Westfall-Young
  step-down sobre la familia de 8, que controla el FWER por sí solo. Lo que queda fuera de la
  familia es **exploratorio** y se rotula.
→ Duración: nulo (Mann-Whitney p=0,319; Cliff's δ IA−humano = −0,116). Es un hallazgo, no un fracaso.
→ **Los datos del análisis son el consenso de un panel de tres anotadores ciegos** (Sonnet + 2 Opus),
  no la extracción de una pasada, que sobrestimaba los compromisos humanos (25 → 17).
→ **Los brazos no comparten cartera**: el humano retoma un acuerdo previo en 26/50, la IA en 0/50.
  Cuatro diferencias de encuadre y promesa se sostienen entre gestiones nuevas, corrigiendo por
  las 8; la de confidencialidad no (tentativa). Los compromisos de pago no difieren (9 vs 17).
→ Propuesta con cifras: rúbrica literal, «hoy» es fecha, solo con citas que existen en la
  transcripción (28 vs 29). Ver `docs/decisiones.md` §14.
→ La hoja de escucha del lunes (`data/interim/hoja_escucha_compromisos.csv`) valida a oído las 14
  celdas de compromiso sin unanimidad. Su recuento va a `docs/decisiones.md`.

## Reglas de trabajo
- Español (es-CO) en todo lo que ve el evaluador. Código e identificadores en inglés.
- **Prohibido inventar o redondear cifras a ojo.** Todo número del reporte sale de `results.json`.
- Ningún número se escribe a mano en el HTML.
- Escala: 100 filas. CSV, no parquet. Sin capas que no cambien el resultado.

## Hecho =
`make report` corre en un clon limpio · el PDF da exactamente 2 páginas sin contenido cortado ·
ningún audio ni transcripción en `git log` · cada afirmación del reporte tiene su número detrás.
