# Brief de diseño

Para quien vaya a trabajar la parte visual del informe —una persona o una herramienta como
Claude Design— con acceso a este repositorio. Todo lo que hay que saber está aquí; lo que no
está aquí, está enlazado.

## Qué es esto

Un informe de **dos páginas A4** que compara 50 llamadas de cobranza hechas por gestores humanos
con 50 hechas por el agente de voz de Creceré AI. Es la entrega de una prueba técnica; lo
califica Creceré y el lector para el que está escrito es **el presidente de un banco**.

El encargo, con sus palabras: «muy visual, pocas palabras, bullets cortos, métricas visibles,
gráficos solo cuando aporten», «mostrable al presidente de un banco», y «no premiamos
complejidad ni volumen: premiamos criterio, claridad y capacidad de terminar bien».

- Se ve aquí: <https://mauriciosf2004.github.io/crecere-humanos-vs-ia/report/>
- Se imprime desde `report/index.html`. Se abre como adjunto, sin conexión.

## Qué cuenta el informe, en orden

**Página 1 — la decisión.** Sí hay diferencias entre canales, pero dicen cómo cobra cada uno,
no cuál cobra mejor: los dos no atendieron la misma cartera. Recomendación: corregir el guion de
los dos canales antes de escalar, y medir la conversión con un piloto aleatorizado. Debajo,
cuatro alertas de cumplimiento con la frase literal que las produce, y el gráfico de las ocho
conductas con su margen de error.

**Página 2 — la evidencia.** El recorrido de la llamada sobre una sola regla de 0 a 50: hasta
dónde llega la conversación, cómo queda quien contesta, y qué hace el agente cuando el deudor
dice que no puede pagar. Cierra con cinco acciones numeradas, ordenadas por plazo.

## Lo que se puede tocar y lo que no

| Archivo | Qué es | ¿Se toca? |
|---|---|---|
| `report/template.html.j2` | La maqueta: CSS y estructura HTML con marcadores `{{ }}` | **Sí.** Es todo el trabajo visual |
| `src/charts.py` | Los dos gráficos, dibujados en SVG desde los datos | Solo la geometría y las clases CSS; nunca los números |
| `src/results.py` | Arma cada cifra y cada frase desde los datos | **No.** Ahí viven las cifras y los guardas que hacen fallar el informe si una deja de sostenerse |
| `data/public/results.json` | Todo lo que se imprime | **No.** Se regenera |
| `report/index.html` | El informe | **No a mano.** Lo produce `make report` |

La regla que no se negocia: **ninguna cifra se escribe a mano.** Si un marcador `{{ }}` se
sustituye por un número pegado, el cambio se descarta entero.

## Cómo se comprueba

```
make report    # regenera results.json e index.html desde los datos
make verify    # imprime a PDF con Chrome y falla si no son exactamente dos páginas
make check     # formato, lint y 35 tests
```

Un cambio se acepta solo si los tres pasan. La puerta de las dos páginas no la decide nadie a
ojo: la decide Chrome. Hoy la página 1 tiene unos 5 mm de holgura y la 2 unos 10.

## El sistema visual, ya decidido

Sale de la identidad de Creceré AI, extraída de su propio sitio, y de una regla que lo gobierna:
**el rosa es identidad, no información.**

| Papel | Valor | Por qué |
|---|---|---|
| Firma de marca | `#f06ecf` | Solo el filete de la cabecera. Tiene 2,67:1 de contraste sobre blanco: no puede llevar texto ni datos |
| Rótulos | `#7a2c68` | El magenta que sí se lee: 8,80:1 |
| Serie IA | `#1f3d7a` | Azul |
| Serie humanos | `#a8631b` | Ocre. Las dos series se separan 21,8 de ΔL* en gris |
| No concluyente | `#6f747c` | Gris, con línea más fina |
| Alerta | `#8c2f23` | Solo el título del bloque de cumplimiento |
| Tinta, atenuado, filetes | `#1f1f1f`, `#737373`, `#e6e6e6` | Grises de saturación cero |

Tipografía: **Poppins** (400, 600, 700) en títulos y rótulos, embebida en base64 dentro del
HTML para que se componga igual en cualquier máquina; el cuerpo va en la sans del sistema con
Liberation Sans como respaldo de métrica conocida. El gesto que más identifica a la marca es el
rótulo en mayúsculas, peso 600 y tracking de 0,2 a 0,25 em.

Dos restricciones más: **se imprime y se fotocopia en blanco y negro**, así que ninguna
información puede depender solo del color —las series van también por forma (círculo/rombo) y
por relleno (sólido/trama/vacío)—; y **los denominadores son distintos entre filas** (19, 22 y
50), por lo que en la página 2 nada se reescala a porcentaje: todo se mide contra la misma
regla de 0 a 50.

## Lo que se pide

Mejorar composición, ritmo, jerarquía y detalle tipográfico **sin cambiar qué se dice ni en qué
orden**. Lo que más valor tiene ahora mismo:

1. La cabecera de la página 1: que la decisión se lea en tres segundos.
2. La tabla de alertas: que la cita literal se lea como evidencia, no como decoración.
3. El recorrido de la página 2: proporciones, aire entre paneles, leyendas.
4. El cierre de cinco acciones: que se lea como un plan y no como una lista.

## Lo que no se pide

- Rediseñar los gráficos desde cero: la escala, el marco de 50 y las longitudes se calculan.
- Reescribir textos: el veredicto, la salvedad legal y las cinco acciones son juicios y salen
  de `results.json`. Se maquetan, no se editan.
- Explorar paleta: está decidida y medida.
- Tocar la paginación: la decide `make verify`.

Cómo se llegó hasta aquí, con cada decisión y el dato que la sostiene: `docs/decisiones.md`. El
control de calidad y por qué el informe dice lo que dice: `docs/control-de-calidad.md`.
