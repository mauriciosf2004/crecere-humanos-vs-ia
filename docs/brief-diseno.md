# Brief de diseño

Para quien vaya a trabajar la parte visual del informe —una persona o una herramienta como
Claude Design— con acceso a este repositorio. Todo lo que hace falta saber está aquí; lo que no
está aquí, está enlazado.

## Qué es esto

Un informe de **dos páginas A4** que compara 50 llamadas de cobranza hechas por gestores humanos
con 50 hechas por el agente de voz de Creceré AI. El lector para el que está escrito es
**el presidente de un banco**, que le va a dar noventa segundos.

El encargo, con sus palabras: «muy visual, pocas palabras, bullets cortos, métricas visibles,
gráficos solo cuando aporten», «mostrable al presidente de un banco», y «no premiamos
complejidad ni volumen: premiamos criterio, claridad y capacidad de terminar bien».

## Cómo verlo

- Publicado y siempre idéntico al repositorio: <https://mauriciosf2004.github.io/crecere-humanos-vs-ia/report/>
- En local: `make report && make verify` deja el PDF en `/tmp/crecere-report.pdf`, y
  `pdftoppm -r 150 -png /tmp/crecere-report.pdf pagina` lo convierte en `pagina-1.png` y
  `pagina-2.png`. Juzgar siempre sobre el PDF: es lo que se imprime.

## Qué cuenta, y en qué orden (esto no cambia)

**Página 1 — la decisión.** Cabecera con el filete de marca y el título. Veredicto en dos
frases: hay diferencias, pero dicen cómo cobra cada canal y no cuál cobra mejor, porque no
atendieron la misma cartera. Recomendación en línea propia, entre filetes: corregir el guion de
los dos canales y medir con un piloto aleatorizado. Debajo, la tabla de cuatro alertas de
cumplimiento, cada una con **la frase literal del guion** que la produce, sus conteos sobre 50,
la acción y la norma. Al pie, el gráfico de efectos de las ocho conductas con su margen de error.

**Página 2 — la evidencia.** Una regla única de 0 a 50 llamadas y tres paneles medidos contra
ella: hasta dónde llega la conversación (embudo), cómo queda quien contesta (partición de 50) y
qué hace el agente cuando el deudor dice que no puede pagar (barras de 19 y 22 sobre la misma
regla). Cierra con los hallazgos y su acción, en tres columnas por plazo, y una línea de
procedencia.

## Lo que se puede tocar y lo que no

| Archivo | Qué es | ¿Se toca? |
|---|---|---|
| `report/template.html.j2` | La maqueta entera: CSS y estructura HTML con marcadores `{{ }}` | **Sí.** Aquí está todo el trabajo |
| `src/charts.py` | Los dos gráficos, emitidos como SVG desde los datos; sus clases CSS se estilan desde la plantilla | La geometría (anchos de columna, alturas de barra, espaciados) sí; los números y la escala, no |
| `src/results.py` | Arma cada cifra y cada frase, y falla si el análisis deja de sostener una | **No** |
| `data/public/*.json` | Todo lo que se imprime | **No.** Se regenera |
| `report/index.html` | El informe | **Nunca a mano.** Lo produce `make report` |

La regla que no se negocia: **ninguna cifra se escribe a mano.** Si un marcador `{{ }}` aparece
sustituido por un número pegado, el cambio se descarta entero.

## Cómo se acepta un cambio

```
make report    # regenera results.json e index.html desde los datos
make verify    # imprime con Chrome y falla si no son exactamente dos páginas
make check     # formato, lint y 35 tests
```

Los tres en verde, o no entra. La puerta de las dos páginas no la decide nadie a ojo: la decide
Chrome. Hoy la página 1 tiene **15 mm** de holgura sobre el pie y la página 2 **4 mm**. Un cambio
de tipografía en el cuerpo se come esa holgura: los tamaños están donde están porque caben. En la
página 2 el alto lo fija la columna más alta del plan («90 días»); una tarjeta que la supere manda
el informe a tres páginas.

## El sistema visual, ya decidido y medido

Sale de la identidad de Creceré AI, extraída de su propio sitio, con una regla que lo gobierna
todo: **el rosa es identidad, no información.**

| Papel | Valor | Por qué |
|---|---|---|
| Firma de marca | `#f06ecf` | Solo el filete de la cabecera. 2,67:1 sobre blanco: no puede llevar texto ni datos |
| Rótulos de sección | `#7a2c68` | El magenta que sí se lee, 8,80:1. Mayúsculas, peso 600, tracking 0,2-0,25 em: es el gesto que más los identifica |
| Serie IA | `#1f3d7a` | Azul |
| Serie humanos | `#a8631b` | Ocre. Las dos series están a 21,8 de ΔL* en gris: se distinguen fotocopiadas |
| No concluyente | `#6f747c` | Gris, con línea más fina |
| Alerta | `#8c2f23` | Solo el título del bloque de cumplimiento |
| Tinta · atenuado · filetes · lavado | `#1f1f1f` · `#737373` · `#e6e6e6` · `#fafafa` | Grises de saturación cero |

Tipografía: **Poppins** (400, 600, 700) en títulos y rótulos, embebida en base64 dentro del HTML
para que se componga igual en cualquier máquina; el cuerpo va en la sans del sistema con
Liberation Sans como respaldo de métrica conocida (un Linux sin fuentes se iba a tres páginas
hasta que se resolvió así). Cifras en monoespaciada tabular.

Dos restricciones que vienen del uso, no del gusto: **se imprime y se fotocopia en blanco y
negro**, así que nada puede depender solo del color —las series van también por forma
(círculo/rombo) y por relleno (sólido/trama/vacío)—; y **los denominadores son distintos entre
filas** (19, 22 y 50), por lo que en la página 2 nada se reescala a porcentaje: todo se mide
contra la misma regla.

## Los dos gráficos, para estilarlos desde el CSS

Los SVG van inline y heredan la hoja de estilos. Clases:

- **Gráfico de efectos** (`forest`): `.axis-zero`, `.axis-tick`, `.axis-label`, `.axis-title`,
  `.row-label`, `.row-value`, `.ci` (la línea del intervalo), `.pt` (la marca), y los
  modificadores `.pos` / `.neg` / `.null` que dan el color según dirección y significancia.
- **Recorrido** (`recorrido`): `.rc-rule` y `.rc-tick` (la regla), `.rc-frame` (el marco de 50
  detrás de cada barra), `.rc-tag` (IA / HUM junto a cada barra), `.rc-bar` con `.ia` / `.human`
  y `.solid` / `.hatch` / `.hollow` / `.dots` (los rellenos), `.rc-count` (el conteo al final),
  `.rc-label`, `.rc-title`, `.rc-legend`, `.rc-swatch`, `.rc-caption`. La trama es un
  `<pattern>` real de SVG; Chrome la imprime bien.

Las geometrías (columna de rótulos, alto de barra, separaciones) son constantes al inicio de
`forest()` y `recorrido()` en `src/charts.py`. Se pueden ajustar; las longitudes y la escala se
calculan y no se tocan.

## Lo que se pide

La estructura, el contenido y el orden son definitivos. Lo que se pide es **oficio**: que las
dos páginas, impresas y puestas sobre una mesa, parezcan hechas por alguien que diseña papel para
bancos y no por alguien que redacta bien. En concreto, por valor:

1. **La página 1 en tres segundos.** Que el ojo entre por el veredicto, caiga en la
   recomendación y solo después llegue a la tabla. Hoy los tres compiten un poco. Escala
   tipográfica, aire y peso; no más texto.
2. **La tabla de alertas.** Que la cita literal se lea como evidencia bajo el rótulo y no como
   decoración: cursiva, cuerpo, color, sangría. Que las cuatro filas tengan el mismo ritmo.
3. **El recorrido.** Proporción entre la regla, los rótulos, las barras y las leyendas; que los
   tres paneles se lean como tres capítulos del mismo objeto.
4. **El plan de tres columnas.** Que se lea como un calendario, no como tres listas.
5. **La cabecera y el pie**, que son lo que da la sensación de documento.

«Wow» aquí significa **precisión y contención**, no decoración: la referencia es el propio
sitio de Creceré —Poppins, el rótulo con tracking, grises neutros, un solo acento— y la calidad
de un informe de banca central impreso.

## Lo que no se pide

- Rediseñar los gráficos desde cero ni cambiar qué codifican: la escala, el marco de 50, las
  longitudes y los rellenos redundantes con el color están decididos por legibilidad.
- Reescribir textos: el veredicto, la salvedad legal, las citas y las cinco acciones salen de
  `results.json`. Se maquetan, no se editan.
- Explorar paleta o tipografía de marca: están decididas y medidas.
- Tocar la paginación, añadir una tercera página o depender de una fuente externa.

## Qué se entrega de vuelta

Un commit —o los archivos— que toque `report/template.html.j2` y, si hace falta, las constantes
de geometría de `src/charts.py`, con `make report`, `make verify` y `make check` en verde.
Ninguna cifra pegada a mano; los marcadores `{{ }}` se quedan donde están.

Cómo se llegó hasta aquí, con cada decisión y el dato que la sostiene: `docs/decisiones.md`.
Por qué el informe dice lo que dice y cómo se controla su calidad: `docs/control-de-calidad.md`.
