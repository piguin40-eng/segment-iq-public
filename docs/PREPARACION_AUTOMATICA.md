# Preparación automática desde el STL

El panel 0.3 registra el caso y encola una segmentación en una sola transacción. No exige un JSON, una conexión con Ollama ni una segmentación de referencia. El trabajador recupera fuentes del índice local, congela el historial, ejecuta `engine/prepare_profile.py` con el Python de geometría y pasa su resultado al ejecutor de trece etapas. Los perfiles quedan en los datos privados, asociados a cada ejecución.

## Qué se mide y qué se propone

1. Comprueba cierre, orientación de caras, volumen positivo y dimensiones compatibles con una arcada interpretada en mm. No escala.
2. Agrupa aristas circulares y polígonos regulares coaxiales, confirma el vacío axial y paredes internas en 48 direcciones a nueve alturas. Admite entre una y 16 chimeneas verificadas sin exigir un par de anillos concéntricos ni una clasificación comercial de la interfase/implante. Conserva ejes, radios, escalones y diagnósticos de candidatos descartados.
3. Orienta con los ejes medidos y la abertura del arco; en puentes cortos usa el eje longitudinal y secciones del STL. Guarda una transformación rígida reversible. El nombre FDI orienta SUP/INF; si no es deducible, conserva AUTO y lo indica en el perfil.
4. Muestrea el espesor por rayos sobre el STL. Propone TOP como el menor entre la mediana de fondo + 60% de espesor y el percentil 10 oclusal menos 1,5 mm. Es una propuesta inicial, no una altura clínica validada.
5. Busca un corredor continuo con anatomía al menos 1,2 mm por debajo y 1,5 mm por encima del plano propuesto. Los bordes usan percentiles 20–80 del corredor. Los extremos finos pueden acortar el trazado: informa cuántas muestras se omiten y exige revisar cobertura distal. No identifica automáticamente cada diente.
6. Aplica el orden reconstruido del laboratorio: tubos/conos, trazado, seis perfiles, remallado, seguridad adaptada, cemento y separación. Las retenciones son opcionales según el vídeo; solo se construyen y validan cuando el perfil las solicita.

Los radios de exclusión de retenciones son radio de cada asiento +0,9/+0,8 mm. Cemento inicial SUP 0,15 mm; INF/AUTO 0,14 mm. Son parámetros propuestos a partir de referencias, no reglas universales. El marco de trabajo, alturas, anchuras y su procedencia se guardan para revisar y reproducir.

## Protección de interfases y conexiones directas (0.3.2)

El laboratorio exige localizar la chimenea y conservar todo el perímetro funcional, independientemente del tipo de conexión. Se mide la envolvente de los detalles basales, paredes internas y primer cuello estrecho. Se crea una protección circunferencial por conexión con un margen de herramienta de 0,25 mm; este margen no modifica la superficie funcional del STL. Las geometrías hexagonales regulares se ensayan con modelos sintéticos, sin copiar catálogos o piezas terminadas.

Después de remallar y calcular el cemento se añade la protección al núcleo; la primaria intersecta ese sólido con el STL original. Se excluye esa misma región de las retenciones. La limpieza intenta primero tolerancias numéricas finas para evitar modificar las superficies que deben conservarse.

Antes y después de exportar se comprueba el volumen original contenido en toda la envolvente, las distancias de sus vértices de superficie y el paso libre por los ejes de las chimeneas. La comprobación de volumen detecta pérdidas entre los puntos muestreados, no solo en el anillo basal. Fallar esos controles impide marcar la propuesta como completada. La envolvente detectada requiere revisión del técnico: todavía no se valida una biblioteca universal de conexiones, ejes acodados ni detalles arbitrarios sin evidencia geométrica suficiente.

## Iteración y memoria

Desde 0.5.8, las propuestas ejecutadas por el arnés añaden `Comprobacion_extraccion.json`: intersección de primaria con supra trasladada en posiciones discretas. Se ensaya la dirección medida propuesta en `shape_refinement.proposed_insertion_direction_work`, o Z de trabajo si no existe. El informe identifica su origen: es una dirección provisional, no un eje aprobado de inserción. El alivio y la comprobación deben usar la misma dirección. Las colisiones medidas se entregan a la revisión; el informe no certifica el recorrido continuo ni selecciona un eje clínico. El agente puede contrastar otras direcciones explícitas con el inspector de lectura. No se rebaja ningún control geométrico por este ensayo.

Desde 0.5.7, cuando un caso aún no tiene una propuesta terminada, el siguiente intento recupera los parámetros y adaptadores de su último borrador que pasó los controles geométricos. Exige el mismo STL y motor, conserva la revisión que rechazó el acabado y aplica los límites actuales antes de ejecutar. Las mallas anteriores sirven exclusivamente para comparar: la reconstrucción vuelve a partir del STL bruto. El borrador continúa sin aprobar hasta una nueva construcción y revisión. Si el motor cambió o faltan controles, no se hereda ese código. Los informes del visor pertenecen al mismo intento que las imágenes, incluso antes de publicar una propuesta.

Desde 0.5.5, la dirección hacia la corona se determina conjuntamente para la arcada; un implante anterior alto ya no invierte su base por quedar sobre el centroide global. La envolvente incluye los escalones anulares medidos por encima del primer cuello estrecho, sin extenderse por un único anillo de salida oclusal. Las superficies y el volumen protegido se vuelven a comprobar al exportar. Los nuevos perfiles usan `retention_mode=none`, coherente con las retenciones opcionales del vídeo. El agente puede justificar `dual_optional` o `dual_required`; los perfiles históricos sin este campo conservan el modo obligatorio. Omitir surcos nunca permite aceptar fragmentos, pérdida de conexiones ni un mínimo de supra insuficiente.

El trazado se vuelve a medir después de afinarlo: cada borde debe apoyarse en un intervalo continuo del STL, no sumar material a ambos lados de una chimenea. Si el plano propuesto no permite ese apoyo, se busca un plano próximo conservando las reservas y todas las secciones; `height_reference.corridor_plane_adjustment` y `refined_trace_support` guardan el cambio. La validación oclusal mide la supra situada en el mismo intervalo original que la nueva separación, y registra aparte las paredes originales al otro lado de un canal en `unpaired_source_sections`. Estas exclusiones no acreditan espesor suficiente ni ausencia de socavaduras: el agente debe revisar esas zonas y el contorno completo.

Desde 0.5.6, la medición usa la normal de la cara real de separación. Conserva en `vertical_chord_mm` la cuerda Z anterior para contrastar falsos mínimos cuando el rayo salía por un canal inclinado. El nuevo método también detecta paredes oblicuas finas que la medida vertical podía ocultar. La reserva de 0,8 mm no cambia, y una separación nueva sin intervalo completo de supra se registra con espesor cero. Los informes declaran el método y conservan puntos de entrada/salida y dirección. El arnés identifica los scripts cambiados desde cada fallo, para no confundir una fragmentación histórica con el resultado actual.

Desde 0.5.4, si el plano horizontal no permite una primera propuesta, se mide un plano cervical inclinado con las muestras del propio STL. La inclinación anatómica deja de sumarse como si fuera un incremento de metal anterior. El incremento regional conserva su límite de 3 mm, y siguen vigentes el corredor de material, reserva oclusal y controles finales de conexiones. `height_reference` registra el ajuste, sus residuos y la holgura local de los asientos. `bar_plane[:2]` contiene las pendientes; `bar_top_z` es el intercepto y tiene prioridad sobre la copia documental `bar_plane[2]`. TOP, anclajes del trazado y conos utilizan el mismo campo de altura. Esto prepara una propuesta para el agente; no acredita por sí solo la segmentación final, el espesor global ni la inserción. Los errores muestran su causa breve en el visor y conservan el registro técnico completo.

Desde 0.4 también se desglosan la altura anterior y el mínimo de supra de una misma nota. El TOP puede tener altura regional, en vez del plano uniforme inicial, y los conos siguen esa altura. La reserva oclusal se aplica y mide; no se afirma un control global de todas las paredes. Ver [VISOR_Y_B4D.md](VISOR_Y_B4D.md) para los controles, el visor y el uso real de iBar en cemento.

**Aplicar correcciones y rediseñar este trabajo** congela las observaciones del caso y generales existentes al pulsar. Siempre reconstruye desde el STL original; no suma otra vez cambios sobre una malla ya corregida. Una observación posterior queda para la siguiente versión.

El intérprete inicial admite indicaciones simples de más/menos altura, profundidad y anchura. Altura: cifra en mm, o 0,5 mm sin cifra; limita cada ajuste a 1,5 mm y el acumulado a ±2 mm. Anchura/profundidad: amplía o contrae 5 puntos percentiles por borde, acumulado ±10. El informe registra los ajustes efectivos. Indicaciones regionales, contradictorias, no reconocidas o dependientes de adjuntos quedan explícitamente pendientes; no se sustituyen por cambios globales.

El RAG conserva vídeos, capturas, pasos y criterios para consultar y adaptar el motor. Las referencias recuperadas se adjuntan a cada versión; no se ejecuta código incrustado ni se copian mallas. Indexar un vídeo no cambia por sí solo los parámetros ni entrena los pesos del modelo. El orden aprendido está implementado en los scripts versionados; ampliar la interpretación de correcciones requiere comprobar una mejora real antes de promover código.

## Comprobación y límites

Las booleanas usan Mesh64 y el intercambio STL ASCII evita redondear a float32 las intersecciones. La limpieza de primaria conserva el límite histórico de simplificación (máximo 0,007 mm); no remalla el STL del paciente ni elimina piezas para obtener PASS.

Se comprueba cierre, orientación, un componente por pieza, volumen positivo, solapamiento y asientos muestreados; se recargan los STL exportados. Euler se compara antes/después de exportar. En casos automáticos no se predice su valor a partir del número de conexiones: la anatomía original puede contener otras asas. En perfiles de referencia se conserva su topología esperada explícita. Registrar la topología no demuestra que todos los canales sean anatómicamente correctos.

PASS significa controles geométricos superados y diseño pendiente de revisión. No calcula espesor mínimo global, trayectoria de inserción, oclusión ni cobertura diente por diente. No equiparar las holguras del corredor muestreado a espesor mínimo de la pieza completa. Las retenciones requieren inspección de su red.

Si el intento falla sin geometría válida, el trabajo queda en error y conserva las etapas, historial y diagnóstico descargable. Desde 0.5.8, un borrador que superó los controles geométricos pero necesita ajustes de diseño queda en `needs_review`, con el intento y sus pendientes identificados en `Agente/Borrador_no_aprobado.json`. No es una propuesta aceptada. Reintentar crea una versión nueva. Reiniciar el servicio marca las ejecuciones activas interrumpidas; no las presenta como terminadas. No aumentar tolerancias ni ocultar fallos para simular autonomía.
# Centrado pendiente de rediseño

La indicación «conexiones por el medio de la barra» activa el requisito de centrado. Si el campo nominal no permite centrar automáticamente el trazado, la preparación conserva la semilla medida y el diagnóstico `pending_agent_redesign` para que el agente pueda replantear la forma. No cambia ejes ni declara resuelto el centrado. `center_connections` permanece activo y la geometría final debe superar el control de hombros bilaterales; el fallo de una estimación inicial no se transforma en un error de carga ni obliga a pedir un JSON al técnico.
# Corrección de orientación en 0.5.15

Los círculos aislados que no aportan evidencia axial de chimenea ya no deciden
el sentido de las conexiones. La orientación de arcada conserva el sentido
medido junto al asiento y sus protecciones; no lo invierte por segunda vez
según el centroide del conjunto. Esto evita situar las referencias funcionales
al lado opuesto y detener la preparación con una falsa falta de altura.

Pruebas de regresión: círculos aislados, arcada inclinada cuyo centroide queda
por debajo de los asientos, conservación de extremos de las referencias bajo
transformación rígida, chimeneas y preparación de planos. Los 18 ensayos de
`test_chimneys.py` y `test_inclined_profile.py` pasan. El caso que motivó la
corrección supera la preparación que antes fallaba. La generación posterior
y su revisión siguen siendo necesarias; esta corrección no aprueba geometrías
anteriores ni modifica el STL original o las tolerancias del caso.
# Chimeneas y anatomía distante · 0.5.18

La comprobación axial se limita al tramo medido entre las características circulares de cada chimenea, con 0,05 mm de margen de detección en sus extremos. Una intersección distante con otra región del STL no elimina una conexión cuya chimenea medida está vacía y conserva paredes interiores en varias alturas. Se mantienen el rechazo de material dentro del canal y la comprobación circunferencial; no se modifican las protecciones ni las tolerancias de la separación. En caso de referencia, dos ejes descartados tenían intersecciones a 10–12 mm de la base, fuera de sus tramos medidos de unos 5 mm.

Desde 0.5.19, la validación final aplica la misma localización del canal. Conserva además el control de material NUEVO fuera de él, contrastando las intersecciones con los intervalos orientados del STL original. Un techo distante que ya estaba en el diseño se registra aparte y no se confunde con una chimenea obturada; un tapón nuevo dentro o fuera de su abertura sigue fallando. Las interpretaciones ambiguas no permiten excluir intersecciones remotas. Los perfiles sin longitud de canal medida conservan el control histórico de todo el eje. Esto no certifica el acceso del destornillador ni la trayectoria clínica, y no modifica la geometría protegida ni las exigencias de supra.


## Preparación y referencias medidas · 0.5.22

Los puentes con tres conexiones alineadas podían producir un booleano NumPy en `center_connections` y detenerse al guardar el perfil. La clasificación se convierte ahora a `bool` nativo; no se cambian las protecciones ni los límites de geometría. El registro visible incluye los errores de serialización en lugar de ocultarlos bajo un mensaje genérico.

La ingesta de STL y escenas Blender genera un inventario medido y lo indexa en el RAG. Las escenas se abren con scripts deshabilitados; sus modificadores se documentan, sin ejecutar historiales ni copiar geometría terminada. Para objetos ocultos se reconstruye la transformación almacenada; los casos con restricciones no resolubles quedan sin medida mundial. La versión del archivo y la del lector se conservan como límite de interpretación.

Los ejemplos adjuntos expresamente al caso se fijan además en `Aprendizajes_caso.json` y `Contexto.case_learning_assets`, fuera del top-k del RAG. Se incluyen informes de geometría, imágenes y documentos de referencia con identidad y hash; las mallas originales siguen siendo referencias de lectura. Un mismo nombre de archivo no implica la misma geometría. Este inventario y el paso de contexto no certifican que la nueva segmentación cumpla: deben comprobarse la ejecución, sus piezas y sus medidas.

## Recuperación de borradores inferiores · 0.5.23

La recuperación buscaba únicamente `Primaria_SUP_PROPIA.stl` y `Supra_SUP_PROPIA.stl`. Un intento inferior que superaba los controles geométricos pero era rechazado en revisión acababa en error y no se recuperaban sus ajustes. Ahora exige ambos STL de la arcada medida (`SUP` o `INF`) y rechaza discrepancias con el perfil base. Conserva el rechazo y sus pendientes bajo `needs_review`; no cambia los límites ni aprueba el borrador.

## Retenciones pequeñas y continuación · 0.5.24

Una superficie segura de 195 caras se reducía a dos caras y Tissue producía una red vacía. La simplificación conserva al menos 32 caras cuando existen; la misma superficie genera ahora 33 caras, 57 vértices y 85 aristas duales en Blender 3.6. Se registra la preparación y se rechazan herramientas vacías con un diagnóstico explícito. Los controles de retención, espesor y conexiones permanecen activos; construir una herramienta no aprueba la segmentación.

Al continuar, el candidato numérico guardado más reciente tiene prioridad sobre un borrador medido anterior. Se comprueban fuente, perfil base, correcciones, protocolo y código permitido. Solo una migración de motor revisada por hashes permite recuperar esos adaptadores; los módulos inmutables se copian de la instalación actual y se vuelve a planificar y medir. El ejecutor muestra la causa del error de cada etapa en lugar del envoltorio del subproceso.

## Exportación de la secundaria · 0.5.25

La primaria conservaba la topología indexada antes de exportar, pero la supra se cargaba desde un STL intermedio que podía unir contactos coincidentes. En el caso superior diagnosticado, 21 pares de vértices presentes en la anatomía de entrada cambiaban el Euler de −14 a −35 al reimportar. No dependían de la altura o anchura del separador.

La etapa 10 prepara ahora ambas piezas desde sus mallas indexadas. Para la supra aplica la misma separación numérica de contactos (máximo 0,000001 mm), sin simplificar ni cerrar agujeros, y comprueba los STL en coordenadas de trabajo y del original. Guarda `Supra_export.npz`, `Supra_export.stl` y `Exportacion_supra.json`; validación y escena final consumen esa misma secundaria. Los intermedios y el STL original se conservan. La migración solo recupera adaptadores de forma permitidos y ejecuta los módulos nuevos.

En la secundaria del intento `ID_PRIVADO_NO_PUBLICADO/01`, la comprobación conserva una pieza cerrada, Euler −14 y género 8 en ambos sistemas de coordenadas; el cambio volumétrico es aproximadamente −0,00000000418 mm³. La corrección de exportación no resuelve los defectos de espesor o extracción del diseño: siguen sujetos a los controles existentes y a una nueva revisión del agente.
