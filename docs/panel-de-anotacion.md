# Panel de anotación

La extracción original fue una sola pasada de un solo modelo. Para no depender de ella, cada
llamada la anotan tres agentes internos de Claude Code, cada uno por su cuenta, y cada celda se
queda con la respuesta de al menos dos de tres. `src/annotate.py` guarda sus respuestas, vota y
mide el acuerdo; no llama a ningún modelo. La extracción original solo vuelve a entrar como fuente
de citas para la regla literal de fecha (abajo).

| Rol | Modelo | Qué hace |
|---|---|---|
| clasificador | Sonnet | aplica la rúbrica |
| auditor | Opus | aplica la rúbrica |
| reauditor | Opus | aplica la rúbrica exigiendo cada criterio al pie de la letra |

## Qué hace que el voto signifique algo

- **Ninguno ve lo que respondieron los otros**, ni la extracción original: se les pide leer
  solo la rúbrica y su carpeta. Si el auditor leyera al
  clasificador, se anclaría en su respuesta y dos votos iguales ya no serían dos opiniones.
- **Ninguno sabe de qué brazo es la llamada.** Las transcripciones se copian a
  `data/interim/panel_input/<uuid>/`, sin la carpeta `humano/` o `ia/` en la ruta. El contenido
  sí puede delatar a un agente de IA —se presenta, habla con guion—, y eso no se puede ocultar.
- **Leen las dos transcripciones** cuando existen: large-v3-turbo y large-v3. Un error del
  transcriptor en una rara vez coincide con el de la otra.
- **La rúbrica es la misma que usó la extracción original** (`src/rubric.md`, sin editar), y la
  salida se valida contra el mismo esquema (`src/schema.json`).

## Lo que no mide

Tres anotadores de acuerdo miden consistencia, no verdad. Comparten la rúbrica y, siendo dos
modelos de la misma familia, parte de sus sesgos. El acuerdo no sustituye escuchar: separa las
celdas firmes (3 de 3) de las frágiles (2 de 3 o sin mayoría), y eso dice dónde está la
incertidumbre.

## Instrucciones

Estas son las instrucciones literales que recibe cada agente. `<carpeta>` es la carpeta de la
llamada en `data/interim/panel_input/`.

### Comunes a los tres roles

> Eres anotador en un análisis de llamadas de gestión de cobranza. Tu única fuente de verdad
> es la rúbrica de `src/rubric.md`: léela completa antes de anotar.
>
> Después lee las transcripciones de la llamada en `<carpeta>`: `transcripcion_a.txt` y, si
> existe, `transcripcion_b.txt`. Son dos transcripciones automáticas de la misma llamada,
> hechas con modelos distintos. Donde difieran, quédate con la lectura que tenga sentido en la
> conversación.
>
> Lee solo esos archivos. No abras ningún otro archivo del proyecto.
>
> Responde cada campo exactamente como indica la rúbrica. Cada cita debe copiarse literal de
> una de las dos transcripciones, en el orden en que aparece; si necesitas unir dos trozos,
> sepáralos con « … ». Si un campo no se puede determinar, responde null. No uses nada que no
> esté en la rúbrica o en las transcripciones. En call_id pon el nombre de la carpeta.

### Por rol

- **clasificador** y **auditor:** *Aplica la rúbrica tal como está escrita.*
- **reauditor:** *Aplica la rúbrica exigiendo cada criterio al pie de la letra: marca un
  positivo solo si la transcripción cumple todas sus condiciones, y lee la llamada entera antes
  de marcar un negativo, porque la frase puede estar en cualquier punto.*

## Cómo se ejecutó

1. `python -m src.annotate --stage` copia las transcripciones limpias a `data/interim/panel_input/<uuid>/`.
2. El script `workflows/panel-anotacion.js` se ejecutó con el tool Workflow de Claude Code, en tres
   lotes (2, 40 y 58 llamadas), con `args = { root, calls, schema }`.
3. `python -m src.annotate --from-workflow <salida del workflow>` guarda cada respuesta y vota.

Los ejemplos entre comillas de `src/rubric.md` son frases inventadas con la misma función que los
que leyó el panel: ninguno reproduce lo dicho en una llamada.

Después del voto se aplica una única regla determinista: en la propuesta con cifras, «hoy» cuenta
como fecha, como dice la rúbrica. El panel no lo había aceptado cuando la fecha era el vencimiento de
la oferta. La celda solo cambia si alguna anotación —del panel o de la extracción— cita un monto y
«hoy», y esa cita existe en la transcripción. Ver `docs/decisiones.md`, §14.

## Segunda rúbrica: desenlace y reacción del interlocutor

El mismo panel, con el mismo script y las mismas instrucciones, anotó una segunda rúbrica:
`src/rubric_desenlace.md` (esquema `src/schema_desenlace.json`). Mide cómo termina la llamada,
incluido el acuerdo parcial, cómo está el interlocutor al final y qué hace el agente cuando el
interlocutor expresa una dificultad. Se congeló antes de anotar (`docs/hipotesis.md` §7) y se probó
con 6 llamadas; las aclaraciones de redacción están en `docs/decisiones.md` §15. Se invoca con
`args.rubric = "src/rubric_desenlace.md"`, y `uv run python -m src.disposition --from-workflow <salida>`
guarda, vota, ancla y calcula los cortes.

El panel es reanudable: si una corrida se interrumpe, se guardan las anotaciones que sí salieron
y la siguiente se lanza con `args.jobs = [[brazo, uuid, rol], ...]`, solo con lo que falta. Así se
completaron las 300 anotaciones del desenlace en dos tandas.

