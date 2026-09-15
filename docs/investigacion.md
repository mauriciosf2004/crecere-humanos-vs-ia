# Investigación previa a la ampliación del análisis

Aquí queda lo que se revisó antes de ir más allá de las ocho conductas binarias. Es investigación
documental: no se corrió ningún modelo sobre las llamadas. Hubo cinco frentes (voz, texto, quién
habla, producción y KPIs de banco). En cada uno, un agente investigó y otro volvió a abrir las
fuentes primarias; cuando discreparon, manda el verificador. Rótulos: *(tercero)*, fuente no
oficial; *(sin confirmar)*, fuente primaria ilegible; *(no reverificado)*, el verificador no la
reabrió.

## 1. Por qué esta investigación

Las ocho variables se definen por la **presencia** de una frase del agente, citada y anclada en la
transcripción (`decisiones.md` §1 y §11). Eso las hace auditables e inmunes al error de separación de
hablantes, pero deja tres huecos. La pregunta en los tres es la misma: ¿hay un instrumento que lo
mida sin reintroducir un error distinto por brazo?

1. **La reacción del deudor.** Es lo emocional comparable entre brazos: la «emoción» de la IA es un
   ajuste del motor de voz (TTS).
2. **El desenlace en lenguaje de banco.** El compromiso con fecha y monto (9 de 50 en IA, 17 de 50 en
   humanos) no separa un acuerdo parcial de uno total, ni un rechazo de un aplazamiento.
3. **La escala.** Qué parte del método sobrevive a cientos de miles de llamadas, y a qué costo.

## 2. Modelos de voz en español para emoción y paralingüística

**Conclusión.** No existe un modelo de emoción por voz documentado que se haya entrenado con habla
natural en español o validado con audio telefónico de 8 kHz. Los datos de la tabla salen de las
fichas; como los modelos quedaron descartados, el verificador no las reabrió.

| Modelo | Con qué se entrenó | Español | Licencia |
|---|---|---|---|
| `somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD` | MESD: habla actuada mexicana, clips de ~1 s en estudio; su 93,08 % es sobre ese material | Nativo, actuado | Apache-2.0 |
| `emotion2vec/emotion2vec_plus_large` | ~40.000 h pseudoetiquetadas sin fuentes publicadas; preentrenamiento de 262 h solo en inglés | Evaluado en 9 idiomas, ninguno español | Propia (FunASR) |
| `FunAudioLLM/SenseVoiceSmall` | >400.000 h para transcripción | Emoción solo en mandarín, cantonés, inglés, japonés y coreano | MIT / FunASR |
| `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` | MSP-Podcast, en inglés | No | CC-BY-NC-SA-4.0 |
| Comunitarios (`pollitoconpapass/...-spanish-v5`, `DrishtiSharma/...-v2`) | No declarado; el segundo no tiene ficha | Sin evidencia | MIT / ninguna |

**Por qué no se usan hoy.**
- **Validez.** Es habla actuada o de otro dominio. En llamadas reales de emergencia (CEMO), la
  precisión fue de 45,6 % en 4 clases, frente a 63 % en habla actuada *(no reverificado)*.
- **8 kHz.** Los modelos esperan 16 kHz. En EMO-DB, bajar a 8 kHz costó ~3,3 puntos, y ~7 con μ-law
  *(no reverificado)*.
- **Voz TTS y mono.** La emoción de la IA describe el motor. Aislar al deudor exige diarizar o
  atribuir, y las dos vías se equivocan distinto por brazo (§4).
- **Privacidad y potencia.** La voz no se anonimiza sin destruir la prosodia. Con 50 llamadas por
  brazo, solo se detecta d ≈ 0,56 con 80 % de potencia.

**Qué se propone.** En esta entrega, la reacción del deudor se anota solo por texto, con el panel
ciego, clases del dominio, cita y escucha por brazo, rotulada como exploratoria. Si la escucha no la
valida, va a `decisiones.md` y no al informe. Lo acústico queda para producción, con dos canales:
- Primero, Silero VAD (MIT, 8 kHz nativo) y praat-parselmouth (GPL-3.0) sobre el canal del deudor.
  Huang et al. (2022) hallaron que la energía de su voz y la duración de la llamada median el efecto
  del gestor sobre la morosidad.
- Después, un clasificador XLS-R propio. MEACorpus sirve de referencia, pero su licencia es
  CC BY-NC 4.0.

## 3. Modelos de texto en español

**Conclusión.** Ningún modelo público en español se entrenó con llamadas, y menos de cobranza. El
obstáculo principal no es el idioma: es la unidad de análisis.

| Modelo | Datos | Métrica en su dominio | Licencia |
|---|---|---|---|
| `pysentimiento/robertuito-sentiment-analysis` | TASS 2020, tuits; máximo 128 tokens | macro-F1 70,2 | TASS: prohíbe uso comercial |
| `pysentimiento/robertuito-emotion-analysis` | EmoEvent, 8.409 tuits, clases de Ekman | macro-F1 55,3 | TASS |
| `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | MNLI + dev de XNLI, ~430 mil pares | 0,845 en XNLI-es | MIT, 0,3B |
| `MoritzLaurer/bge-m3-zeroshot-v2.0-c` | Sintéticos de Mixtral + MNLI + FEVER-NLI | F1 medio 0,59 zero-shot y 0,803 few-shot, casi todo en inglés | MIT, 8.192 tokens |
| `PlanTL-GOB-ES/roberta-base-bne` (MarIA) | 570 GB de la BNE | XNLI 0,8016 | Apache 2.0; obsoleto, remite a BSC-LT |

**Unidad de análisis.** Una llamada mediana tiene unas 330 palabras (recuento local). Trocear no
arregla lo de fondo: sin diarizar, puntuar la llamada mide el guion del agente. El de la IA trae
léxico jurídico («embargos, judicializaciones»), así que un «deudor más negativo con la IA» sería un
artefacto como el del §1. Tampoco la atribución por texto es neutral: el interlocutor quedó
indeterminado en 9 llamadas de IA y en 1 humana (§10).

**Licencias.** TASS dice «any commercial use of the Dataset is strictly prohibited», así que usar
robertuito para una empresa es un riesgo real. De bge-m3-zeroshot, solo la variante `-c` tiene datos
comerciales; la otra mezcla ANLI, WANLI y LingNLI. RigoBERTa-2.0 también es no comercial.

**Experimento posible con mDeBERTa** (opcional; no cambia conclusiones):
- **Qué hace.** Zero-shot local con hipótesis en español («El deudor acepta pagar en una fecha
  concreta»), solo sobre la cita de cierre del deudor que eligió el panel.
- **Cómo se mide.** Acuerdo con el consenso por brazo: AC1 de Gwet y kappa, con IC bootstrap agrupado
  por llamada.
- **Límites.** El acuerdo es una cota superior, el panel no es verdad de referencia y en
  clasificación los LLM no superan a los modelos ajustados (Ziems et al., 2024).

## 4. Quién habla (diarización) en telefonía

DER en CALLHOME, sin ajuste, mono a 16 kHz y collar de 0,25 s (arXiv 2509.26177). El español fue el
más difícil de los cinco idiomas.

| Modelo | Español | Inglés | Licencia |
|---|---|---|---|
| pyannoteAI Precision-2 (API) | 14,3 % | 6,6 % | Comercial |
| BUT-FIT DiariZen | 19,1 % | 7,0 % | Pesos CC BY-NC 4.0 |
| NVIDIA Sortformer v2 | 21,1 % | 15,3 % | CC-BY-4.0 |
| pyannote 3.1 | 27,3 % | 11,5 % | MIT |

**Por qué se mantiene el §1.**
- **Voz sintética.** Ningún benchmark compara voz TTS con voz humana. El sondeo propio (3 de 8
  frente a 0 de 8, Fisher p = 0,2) no demuestra el sesgo, pero tampoco lo descarta.
- **Estructura conversacional.** Las brechas entre grupos vienen sobre todo de ella
  (arXiv 2106.05792), así que igualar la acústica no basta.
- **Fronteras de turno.** Son el fallo dominante, y whisper tesela la línea de tiempo (95 % de
  huecos de 0 ms).
- **Texto y Google.** La atribución por texto logra 86,36 % por enunciado en inglés (SIGDIAL 2023),
  y Google no diariza es-CO.

**Protocolo para revisarla.**
1. 10 llamadas por brazo, con semilla fija. Se etiqueta a mano (RTTM) una ventana de 2 min más los
   últimos 30 s. La rúbrica de frontera se escribe antes y un subconjunto se etiqueta dos veces.
2. Por llamada: DER y sesgo de cada métrica derivada (estimado − referencia). Luego, sesgo
   diferencial IA − humano con IC: semiancho ≈ 0,94·s con t de 18 gl, o Welch si difieren las
   varianzas.
3. La métrica entra solo si la diferencia entre brazos supera |sesgo diferencial| + semiancho. Si
   no, va a `decisiones.md` como validación negativa.

## 5. Qué le importa a un banco

¿Contactamos al titular? ¿Cerramos un acuerdo viable? ¿Se cumplió? ¿Cuánto costó y qué riesgo
corrimos? Las definiciones son de Bridgeforce, consultora de EE. UU.: sirven de referencia, no son
estándar colombiano.

| KPI | Definición | Denominador | ¿Desde la grabación? |
|---|---|---|---|
| Termina en positivo | Aceptación expresa, total o parcial, con fecha y valor (propia) | Llamadas con titular | Sí, como aceptación verbal |
| Promesa de pago (PTP) | Llamadas con compromiso / contactos con el titular | Contactos con el titular | Sí, si se recalcula |
| Contacto con el titular (RPC) | Contactos con el responsable / intentos | Intentos de marcación | No: marcador |
| Promesa cumplida | Dinero recibido a tiempo / dinero prometido | Dinero prometido | No: CRM o piloto |
| Roll / cure rate | Cuentas que pasan de tramo frente a las que se normalizan | Cuentas por tramo | No: core bancario |
| Costo por peso recuperado | Gasto de cobranza / recaudo | Recaudo | No: finanzas y piloto |
| Quejas por 1.000 contactos | Mencionada sin definición formal | Contactos | No: PQRS |
| Horario y frecuencia (Ley 2300) | Contactos fuera de horario o sobre el tope | Contactos | No: marcador |

- **El 9 contra 17 no es PTP.** Su denominador son las 50 llamadas. O se recalcula sobre contactos
  con el titular o se rotula «compromiso con fecha y monto por llamada».
- **«Termina en positivo».**
  - Asobancaria (2022) pide «respuesta expresa», pero no define lo positivo. La escala (sin titular,
    rechazo, aplazamiento, vaga, parcial y total calificadas) es propia y se congela antes de anotar.
  - Queda fuera de la familia de 8 y se reporta también entre gestiones nuevas: 26 de 50 llamadas
    humanas retoman un acuerdo, frente a 0 de 50 de IA.
  - Con una base de 35 %, 20 pp se detectan con 45 % de potencia (36 % entre gestiones nuevas;
    simulación con Fisher).
- **Lo parcial importa.** Para la SFC, un crédito modificado que vuelve a 30 días de mora pasa a
  reestructurado. Las cifras de proveedores (Vozy, Colektia, Sedric) no tienen grupo de control y no
  se usan.

## 6. Marco normativo colombiano relevante

Todo esto es **alerta para revisión de cumplimiento**, no un juicio legal, y aplica a los dos
canales: las grabaciones no dicen si el área existe ni si hay un proceso previsto. Las cifras son
del consenso del panel (`effects.json`).

| Conducta medida | IA | Humano | Norma relacionada | Qué revisar |
|---|---|---|---|---|
| Se presenta desde un área jurídica o de embargos | 43/50 | 1/50 | SFC CE 048/2008: «identificarse debidamente ante el deudor»; Ley 1328, art. 3 c): información «cierta» | Si esa área gestiona la cartera |
| Plantea un proceso legal si no paga | 21/50 | 2/50 | CGP, art. 599: embargo «desde la presentación de la demanda» (espejo no oficial) | Sin embargo prejudicial: inferencia, no texto literal |
| Afirma que la oferta caduca hoy | 27/50 | 1/50 | Ley 1328, art. 3 c) | Política real de condonaciones |
| Promete beneficio en el historial crediticio | 3/50 | 22/50 | Ley 1266, art. 13 (Ley 2157, art. 3): el dato negativo dura el doble de la mora, máximo 4 años | Prometer «limpiar» el reporte |

- **Sanciones y Ley 2300.** La Ley 1266, art. 18 (Ley 2157, art. 14), prevé multas sucesivas de
  hasta 2.000 SMMLV. La Ley 2300 de 2023 fija horario y frecuencia en su art. 3 (aquí no auditable:
  no hay fecha ni hora) y prohíbe consultar «el motivo del incumplimiento» en su art. 7.
- **Pendientes de confirmar.** La exequibilidad de la Ley 2300 (C-278/24) y la T-584/2023 sobre
  presiones indebidas quedan *(sin confirmar)*.
- **Llamadas con IA.** La SIC exige autorización previa, expresa e informada para llamadas
  automatizadas (noticia del 22-jul-2020, Resolución 38281). No se halló norma que obligue a avisar
  que llama una IA *(tercero)*.

## 7. Evidencia externa

**Choi, Huang, Yang y Zhang (2025), NBER w33669.** En una financiera en línea china se tomó al azar
el 10 % de las deudas en mora nueva, y la mitad la llamó una IA con voz sintética reconocible. Con
IA, 21 pp menos prometen pagar y 18 pp menos pagan el mismo día. Sus promesas se cumplen menos: hay
2,3 pp más de mora en la cuota siguiente y 1,3 pp en la duodécima. **Salvedades del verificador:**
los 21 pp comparan definiciones distintas de promesa (en la IA, pago el mismo día; en el humano,
hasta el día siguiente). Los autores piden leerlos «carefully», y su auditoría confirma 84 de 100
promesas de la IA.

**Wang y Zhou (2024), borrador.** En Países Bajos se aleatorizaron 7.839 deudores. El algoritmo
decide a quién llamar y llama el mismo equipo humano. El repago sube de 43,14 % a 53,24 %:
**+10,1 pp** (el 23,40 % es un aumento relativo). No evalúa un agente conversacional.

**Lectura.** La IA puede rendir más priorizando que conversando, y contar promesas puede
sobreestimarla. Eso respalda un piloto de tres grupos cuyo KPI principal sea la promesa cumplida o
el recaudo a 30 días.

## 8. Arquitectura a escala en Google Cloud

Es una propuesta cuantificada, no implementada: la captura va antes que los modelos.

| Componente | Qué resuelve | Condición que cambia costo o validez |
|---|---|---|
| Grabación en dos canales, con cuenta, tramo, campaña, hora y resultado de CRM | Elimina la diarización y habilita la voz del deudor y la Ley 2300 | Speech-to-Text factura cada canal |
| Cloud Storage + Pub/Sub + Cloud Run jobs en `us-central1` | Ingesta por evento | Sin GPU L4 en Sudamérica; Brasil no está en la lista de la SIC y EE. UU. sí |
| Bake-off con 300-500 llamadas propias: Speech-to-Text V2 frente a Whisper large-v3 en L4, WER por brazo | Elegir el transcriptor por datos | El lote dinámico no lista `chirp_3` ni `telephony`; precio de L4 *(tercero)*; no hay WER público en español colombiano |
| Sensitive Data Protection + regex propias | Quita la PII del texto antes del LLM | No redacta audio |
| Gemini por lotes en Vertex AI, con la rúbrica literal | Anota a escala y descarta toda etiqueta sin cita anclada | Gemini 3.8 Flash duplica su precio en 2027; se calibra contra el panel |
| Voz del deudor (fase 2): Silero, parselmouth, XLS-R y Gemini con audio | Reacción acústica | Vertex cuenta 25 tokens de audio por segundo; subir voz cruda exige autorización |
| BigQuery + Looker Studio con vistas por whitelist | Tablero por canal | Los KPIs de resultado exigen el CRM |

**Retención cero en Vertex:** desactivar la caché de 24 h, pedir la excepción al registro por abuso y
no usar Grounding. **Customer Experience Insights**, la opción comprada, no lista sentimiento en
español ni tiene región en Sudamérica.

**Costos.** Los precios unitarios, con URL, fecha y marca de oficial o tercero, están en
`data/reference/costos.json`. Los totales los calcula el código; aquí no se escriben.

**Condiciones legales.** Creceré probablemente es encargada del banco, así que Google sería
subencargado. Hacen falta un contrato de transmisión (Decreto 1377, arts. 24-25) y un país adecuado
(CE SIC 005/2017 y 002/2025). Si hay alto riesgo, se requiere un estudio de impacto de privacidad
(CE SIC 002/2024). Un abogado debe revisar las Leyes 1266 y 2157.

## 9. Qué no se hizo, y por qué

- **Emoción por voz y tono de la IA.** No se midieron: no hay modelo validado, y el tono de la IA es
  un ajuste del TTS (§2).
- **Sentimiento sobre la llamada entera.** No se corrió: mediría el guion jurídico de la IA (§3).
- **Métricas de turno.** No se midieron el reparto del habla, la latencia, las interrupciones ni la
  prosodia del deudor: el §1 sigue en pie (§4).
- **Nube.** No se subieron audio ni transcripciones a ningún servicio: faltan autorización y
  contrato, y la voz no se anonimiza.
- **Licencias no comerciales.** No se usaron robertuito, RigoBERTa, DiariZen, audEERING ni MEACorpus.
- **Motivo del incumplimiento.** No se reintrodujo: fijar ahora su definición sería elegirla después
  de ver los datos.
- **Familia de 8.** Nada nuevo entra en ella ni en Westfall-Young.
- **Infraestructura y benchmarks.** No se construyó infraestructura, no se citan benchmarks de
  proveedores y los 21 pp de Choi et al. no se presentan como una brecha limpia.

## 10. Fuentes

**§2 Voz.** https://huggingface.co/somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD · https://huggingface.co/emotion2vec/emotion2vec_plus_large · https://arxiv.org/html/2312.15185v1 · https://github.com/QwenAudio/SenseVoice · https://huggingface.co/audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim · https://huggingface.co/pollitoconpapass/superb-ser-finetuned-spanish-v5 · https://huggingface.co/DrishtiSharma/wav2vec2-xlsr-spanish-speech-emotion-recognition-v2 · https://arxiv.org/abs/2110.14957 · https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2020.00014/full · https://github.com/NLP-UMUTeam/Spanish-MEACorpus-2023 · https://ideas.repec.org/a/wly/mgtdec/v43y2022i4p1091-1104.html · https://github.com/snakers4/silero-vad · https://github.com/YannickJadoul/Parselmouth

**§3 Texto.** https://huggingface.co/pysentimiento/robertuito-sentiment-analysis · https://arxiv.org/html/2106.09462v3 · https://arxiv.org/html/2111.09453 · https://huggingface.co/pysentimiento/robertuito-emotion-analysis · http://tass.sepln.org/2020/?page_id=109 · https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli · https://huggingface.co/MoritzLaurer/bge-m3-zeroshot-v2.0-c · https://huggingface.co/PlanTL-GOB-ES/roberta-base-bne · https://huggingface.co/IIC/RigoBERTa-2.0 · https://aclanthology.org/2024.cl-1.8/

**§4 Diarización.** https://arxiv.org/html/2509.26177v1 · https://arxiv.org/abs/2106.05792 · https://aclanthology.org/2023.sigdial-1.35.pdf · https://huggingface.co/pyannote/speaker-diarization-3.1 · https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2 · https://huggingface.co/BUT-FIT/diarizen-wavlm-large-s80-mlc · https://www.pyannote.ai/pricing · https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages

**§5 KPIs.** https://bridgeforce.com/insights/credit-union-collections-kpis-2026/ · https://publicaciones.asobancaria.com/wp-content/uploads/Libros/web/Gu%C3%ADa%20de%20mejores%20practicas%20en%20materia%20de%20cobranza%202022.pdf · https://www.superfinanciera.gov.co/publicaciones/10090487/abc-modificacion-en-las-condiciones-del-credito-segun-capacidad-de-pago-del-deudor-10090487/

**§6 Normativa.** https://normograma.crcom.gov.co/crc/compilacion/docs/ley_2300_2023.htm · https://normograma.com/keralty/compilacion/docs/circular_superfinanciera_0048_2008.htm · https://dmsjuridica.com/CODIGOS/LEGISLACION/LEYES/2009/LEY_1328_DE_2009.htm · https://leyes.co/codigo_general_del_proceso/599.htm · https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=34488 · https://normograma.com/documentospdf/icfes2024/compilacion/docs/ley_2157_2021.htm · https://www.corteconstitucional.gov.co/relatoria/2023/t-584-23.htm · https://sedeelectronica.sic.gov.co/noticias/superindustria-recuerda-que-llamadas-automatizadas-o-roboticas-deben-contar-con-autorizacion-del-titular-de-datos-personales · https://megatek.ai/es/regulation/proyecto-ley-inteligencia-artificial-colombia-2025/ *(tercero)*

**§7 Evidencia.** https://www.nber.org/papers/w33669 · https://www.nber.org/system/files/working_papers/w33669/w33669.pdf · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4905228 · https://ncbankruptcyexpert.com/sites/default/files/2024-07/artificial_intelligence_and_debt_collection_evidence_from_a_field_experiment_compressed_0.pdf

**§8 Arquitectura.** https://cloud.google.com/speech-to-text/pricing · https://arxiv.org/html/2509.16375v1 · https://cloudprice.net/gcp/compute/instances/g2-standard-8 *(tercero)* · https://cloud.google.com/sensitive-data-protection/pricing · https://cloud.google.com/vertex-ai/generative-ai/pricing · https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention · https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones · https://docs.cloud.google.com/gemini-enterprise-cx/insights/languages · https://docs.cloud.google.com/contact-center/insights/docs/regionalization · https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=53646 · https://normograma.dian.gov.co/dian/compilacion/docs/circular_superindustria_0005_2017.htm · https://normograma.mintic.gov.co/mintic/compilacion/docs/circular_superindustria_0002_2025.htm · https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=161918&dt=S
