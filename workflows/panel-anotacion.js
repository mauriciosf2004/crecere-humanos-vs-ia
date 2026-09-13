// Script de orquestación que produjo las 300 anotaciones del panel, tal como se ejecutó con el
// tool Workflow de Claude Code. Único cambio respecto a lo ejecutado: la ruta del repositorio,
// que ahora llega como argumento. Invocación: args = { root, calls: [[brazo, uuid], ...], schema }
// con el contenido de src/schema.json. Ver docs/panel-de-anotacion.md.
export const meta = {
  name: 'panel-anotacion',
  description: 'Tres agentes ciegos (Sonnet, Opus, Opus) anotan cada llamada con la rúbrica, sin verse entre sí',
  phases: [
    { title: 'Anotar', detail: 'clasificador, auditor y reauditor por llamada' },
  ],
}

const ROOT = args.root

const ROLES = [
  { rol: 'clasificador', model: 'sonnet', extra: 'Aplica la rúbrica tal como está escrita.' },
  { rol: 'auditor', model: 'opus', extra: 'Aplica la rúbrica tal como está escrita.' },
  {
    rol: 'reauditor',
    model: 'opus',
    extra:
      'Aplica la rúbrica exigiendo cada criterio al pie de la letra: marca un positivo solo si la ' +
      'transcripción cumple todas sus condiciones, y lee la llamada entera antes de marcar un ' +
      'negativo, porque la frase puede estar en cualquier punto.',
  },
]

// Texto literal de docs/panel-de-anotacion.md, con las rutas absolutas.
const common = (stem) => {
  const carpeta = `${ROOT}/data/interim/panel_input/${stem}`
  return (
    `Eres anotador en un análisis de llamadas de gestión de cobranza. Tu única fuente de verdad ` +
    `es la rúbrica de ${ROOT}/src/rubric.md: léela completa antes de anotar.\n\n` +
    `Después lee las transcripciones de la llamada en ${carpeta}: transcripcion_a.txt y, si ` +
    `existe, transcripcion_b.txt. Son dos transcripciones automáticas de la misma llamada, ` +
    `hechas con modelos distintos. Donde difieran, quédate con la lectura que tenga sentido en la ` +
    `conversación.\n\n` +
    `Lee solo esos archivos. No abras ningún otro archivo del proyecto.\n\n` +
    `Responde cada campo exactamente como indica la rúbrica. Cada cita debe copiarse literal de ` +
    `una de las dos transcripciones, en el orden en que aparece; si necesitas unir dos trozos, ` +
    `sepáralos con « … ». Si un campo no se puede determinar, responde null. No uses nada que no ` +
    `esté en la rúbrica o en las transcripciones. En call_id pon el nombre de la carpeta: ${stem}.`
  )
}

phase('Anotar')

const jobs = []
for (const [arm, stem] of args.calls) {
  for (const r of ROLES) jobs.push({ arm, stem, ...r })
}

const results = await parallel(
  jobs.map((j) => () =>
    agent(`${common(j.stem)}\n\n${j.extra}`, {
      label: `${j.rol}:${j.stem.slice(0, 8)}`,
      phase: 'Anotar',
      model: j.model,
      effort: 'high',
      schema: args.schema,
    }).then((anotacion) =>
      anotacion ? { arm: j.arm, stem: j.stem, rol: j.rol, modelo: j.model, anotacion } : null,
    ),
  ),
)

const anotaciones = results.filter(Boolean)
const faltantes = jobs
  .filter((_, i) => !results[i])
  .map((j) => ({ arm: j.arm, stem: j.stem, rol: j.rol }))
log(`${anotaciones.length}/${jobs.length} anotaciones; faltan ${faltantes.length}`)

return { anotaciones, faltantes }
