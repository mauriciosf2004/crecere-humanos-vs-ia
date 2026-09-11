# Pre-registro de hipótesis

Escrito **antes** de construir variables de conducta o resultado, para que la selección de
hallazgos no sea una elección a posteriori entre los p-valores que salieron bien.

> Excepción declarada: la duración ya se midió en el inventario técnico (es una propiedad del
> archivo, no una variable construida). Su resultado se registra abajo como tal.

## Métrica primaria — UNA, declarada de antemano

**Pendiente de decisión.** Candidata: tasa de **compromiso de pago calificado** — compromiso con
fecha resoluble *y* monto explícito *y* confirmación del deudor — sobre el denominador de
llamadas con titular verificado (RPC), no sobre el total.

Todo lo demás es **exploratorio** y se rotula como tal en el reporte. No se aplica corrección por
comparaciones múltiples a la primaria; con potencia individual ya baja, corregir 10 métricas
garantizaría un reporte sin hallazgos.

## Hipótesis direccionales

Cada una declara el signo esperado y una magnitud, no "hay diferencias". Al menos una debe
apostar en contra de la IA.

| # | Hipótesis | Esperado | Estado |
|---|---|---|---|
| H1 | La IA es más **consistente**: menor dispersión en la conducta de la llamada | razón de desviaciones ≥ 1,5 a favor de la IA | pendiente |
| H2 | El humano obtiene compromisos **más concretos** (más elementos de fecha/monto/canal) | ≥ 1 elemento más por compromiso | pendiente |
| H3 | La IA **cumple mejor el guion** de identificación y divulgación obligatoria | ≥ 20 pp a favor de la IA | pendiente |
| H4 | Ante objeción, el humano **recupera** más | ≥ 15 pp a favor del humano | pendiente |
| H5 | La IA **no** acorta la llamada | sin diferencia | **contrastada: se cumple** |

### H5 — resultado

Mediana 171,1 s (humano) vs 149,0 s (IA). Mann-Whitney **p = 0,319**, Cliff's δ = **0,116**
(insignificante), IC95 de la diferencia de medianas **[−89, +87] s**. Levene sobre medianas
p = 0,73: tampoco difiere la dispersión.

Es un nulo informativo: contradice la suposición de que automatizar acorta la gestión.

## Qué limita esta muestra

n = 50 por brazo. Con Fisher exacto bilateral y α = 0,05, **MDE ≈ 29 pp** al 80 % de potencia;
si el denominador baja a RPC (n ≈ 31), **MDE ≈ 37 pp**. Diferencias menores existen pero esta
muestra no las distingue del ruido, y eso se dice en el reporte en vez de esconderse.

Los audios no traen campaña, fecha ni resultado de CRM. No hay forma de verificar que la
asignación humano/IA fuera balanceada, así que **esto es un cuasi-experimento**, no un A/B.
Cualquier control sobre la composición tiene que inferirse del propio audio.
