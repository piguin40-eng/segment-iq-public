# SEGMENT IQ 0.5: ejecución con agente

Al activar `agent_harness: "codex"` en la configuración privada, cada generación y corrección pasa por un agente Codex. No basta con que el asistente local redacte un plan. El supervisor prepara el caso, proporciona herramientas y evidencia al agente, ejecuta Blender, conserva los errores y devuelve el resultado al agente para revisarlo y reintentar.

## Ciclo del caso

1. Medir el STL sin segmentar y recuperar correcciones del caso, criterios generales y ocho referencias del RAG. Congelar el historial al solicitar la ejecución.
2. Crear una carpeta privada en `data/agent_work/JOB`. Incluir STL bruto, perfil medido, documentos del patrón, anotaciones y vista/medidas de la última propuesta. No importar primaria/supra terminadas como fuente geométrica.
3. Ejecutar Codex con shell, visión y edición dentro del workspace. El agente puede ajustar parámetros y programar operaciones numéricas en los adaptadores de altura y forma; no depende exclusivamente de frases reconocidas por el parser.
4. Comprobar qué ha cambiado y conservar intactos STL, conexiones, ejes, orientación, tolerancias y verificadores. Rechazar modificaciones fuera del dominio permitido.
5. Ejecutar las trece etapas. Blender for Dental ejecuta su herramienta de cemento de iBar; las demás etapas son del motor propio. Los intentos quedan separados y el visor muestra sus imágenes reales.
6. Dar al agente la vista final, comparación y controles. El agente acepta una propuesta para revisión, solicita otra adaptación o explica un impedimento. Máximo tres intentos por trabajo; los intentos idénticos no se vuelven a ejecutar.
7. Exponer únicamente el intento terminado que pasa los controles y la revisión del agente. El laboratorio mantiene la aprobación de diseño. Las correcciones y adaptadores del caso se conservan para la siguiente iteración mientras siga siendo compatible la versión del motor.

Desde 0.5.1, `Ultimo_intento.json` entrega los informes, vista y rutas de las mallas al agente también cuando falla la ejecución o un verificador. `Ultima_revision.json` conserva la revisión completa para el siguiente intento. Las evidencias fallidas se recuperan en la siguiente ejecución del mismo caso; no se publican como resultado ni sustituyen el STL de origen.

`Contexto.previous_result` enlaza además las mallas de la última propuesta terminada, identificando su versión y coordenadas, para comparar anchuras y alturas en secciones equivalentes. La referencia de una corrección es esa propuesta; los intentos fallidos se usan como diagnósticos adicionales.

Desde 0.5.2, Resultados muestra una sola propuesta: la publicada o, si no existe, la del intento más reciente con vista final. Su número y estado de revisión quedan visibles. Los STL de trabajo y las versiones anteriores permanecen en el apartado de otros intentos, evitando confundirlos con la descarga de primaria y supra de esa propuesta. Mostrar una propuesta no modifica la decisión del agente ni la convierte en una versión aceptada.

## Configuración e identidad

El ejecutable se detecta en PATH, en la instalación de Codex del escritorio o en el runtime local de SEGMENT IQ para Mac. Se puede fijar `codex_executable` en `config.local.json`. La autenticación usa la sesión Codex del usuario que ejecuta el servicio en ese ordenador; no se copian tokens ni se incorporan al expediente. El instalador Mac configura su binario arm64 e inicia sesión con la cuenta del usuario. Comprobar con `codex login status` desde ese usuario. `agent_timeout_seconds` limita cada fase de razonamiento (900 s por defecto); `agent_max_attempts` tiene un máximo de tres.

En Windows se utiliza el sandbox `elevated` ya configurado en el equipo. PLAN usa workspace-write y REVISIÓN read-only, con aprobación interactiva desactivada. No se usa full-access. `--ignore-user-config` evita cargar conexiones y ajustes ajenos al agente; por ello se selecciona expresamente el sandbox nativo. Si la instalación o autenticación falla, se muestra el error y no se oculta usando otro motor.

Codex usa el modelo predeterminado del CLI, sin fijar otro modelo. Utiliza el acceso y los límites de la cuenta iniciada. El razonamiento ocurre en Codex: las notas, imágenes, código y medidas que lea se envían al proveedor. Blender, RAG y archivos permanecen en el equipo; GitHub solo contiene el código. El chat de consulta de la biblioteca conserva el modelo local Ollama.

## Alcance real

Desde 0.5.20, si el PLAN y su recuperación agotan el tiempo pero dejaron un candidato con cambios geométricos válidos, el supervisor puede construirlo como borrador. Se exige integridad del original, de las conexiones y del código protegido. El registro indica `origin=supervisor_recovery`; no se inventa una respuesta ni una aprobación del modelo. La construcción conserva todos los controles y la propuesta solo puede publicarse tras superar la geometría y recibir la revisión del agente. Si no hay cambios geométricos o el candidato viola restricciones, el timeout sigue fallando.

Al continuar un caso, se puede recuperar ese candidato interrumpido si coinciden exactamente la preparación base, el original, el motor, el protocolo y las correcciones. Solo se copian parámetros y adaptadores permitidos; las piezas se reconstruyen desde el original. La opción de construcción nueva conserva su comportamiento y no hereda candidatos.

Desde 0.5.17, una respuesta explícita de saturación temporal del modelo se reintenta dos veces (10 y 30 segundos) dentro del presupuesto de la misma fase, manteniendo el modelo y el expediente. No se reintentan como saturación los errores de autenticación, límites de uso, geometría o respuestas inválidas. El visor conserva el mensaje estructurado de Codex y cada llamada tiene su propio registro; la saturación persistente se comunica sin declarar una segmentación completada.

Desde 0.5.16, un PLAN que agota su tiempo conserva sus archivos y dispone de una recuperación automática de hasta 240 segundos, sin consumir un intento de Blender. Cada llamada tiene registros y presupuesto separados. Una cancelación se distingue de un timeout y no se reintenta. La recuperación no acepta decisiones incompletas ni publica piezas: necesita una respuesta válida y los verificadores habituales. Los preanálisis se acotan a secciones representativas y lotes pequeños de rayos; los controles completos se ejecutan sobre la construcción. Las mediciones de planes fallidos del mismo origen y motor se ofrecen como evidencia, sin heredar ni ejecutar automáticamente sus scripts o trazados.

Se permite adaptar `shape_refinement.py`, `bar_height.py`, la construcción del separador en `occlusal_safety.py` y un auxiliar `case_geometry.py`, además de las claves de forma del perfil. Esos adaptadores resuelven alturas, techo, trazado, terminaciones y booleanas de separación. Los verificadores externos, la protección funcional original y las tolerancias siguen siendo inmutables. Un cambio fuera de ese alcance queda pendiente con diagnóstico. Se recuperan también las revisiones y el diagnóstico de los dos últimos intentos fallidos del mismo caso para no empezar de cero al iterar.

En 0.5.7, si no existe una propuesta terminada, se puede continuar un borrador con controles geométricos superados y revisión de acabado pendiente. Se comprueban origen, versión del motor e integridad de los informes; solo se heredan los parámetros editables compatibles y adaptadores permitidos. `previous_result.approval=draft_needs_review` identifica su estado y conserva la revisión completa. El supervisor reconstruye desde el original y valida de nuevo; no publica ni aprueba automáticamente el borrador recuperado.

Los adaptadores se filtran como código numérico y se comparan con el motor instalado. Esta política de Python es una comprobación adicional, no un sandbox general para ejecutar código hostil. El laboratorio debe mantener el acceso autenticado del panel. El supervisor ejecuta las etapas y sus validadores; no acepta un PASS escrito por el modelo.

Desde 0.5.21, los errores de sintaxis o imports de un adaptador editable vuelven al agente una vez, durante un máximo de 240 segundos, antes de consumir una construcción. `Correccion_adaptador.json` identifica el archivo y símbolo rechazado. La reparación conserva el criterio numérico y debe superar de nuevo todas las comprobaciones; no amplía imports permitidos, no modifica verificadores y no reintenta cambios en el original ni en código protegido. Las funciones compartidas deben usar nombres públicos. Una respuesta de reparación deja las etapas geométricas pendientes de construir y medir.

La aprobación del agente no acredita espesor global de paredes y márgenes, trayectoria de inserción ni resistencia. No entrena pesos ni promociona automáticamente adaptadores a otros pacientes. Para generalizar una mejora al motor común se necesita evaluación con casos de referencia y aceptación del laboratorio.

Desde 0.5.8, si termina el ciclo con un borrador que pasó los controles geométricos pero cuya revisión pidió ajustes, se conserva como `needs_review`. `Agente/Borrador_no_aprobado.json` identifica el intento y sus pendientes; el visor y los archivos apuntan a ese borrador. No se publica como intento ganador ni permite la aprobación reservada a una generación aceptada. Los fallos sin geometría válida siguen en error. La siguiente corrección puede recuperar los ajustes de ese borrador y reconstruirlos desde el STL original.

Desde 0.5.9, el supervisor añade `Comprobacion_paredes.json`: muestrea la superficie del separador, busca la entrada de supra y mide en la normal propia de su cavidad. Incluye laterales, extremos, ausencia de cavidad y regiones coincidentes con el original para revisar su clasificación. Las muestras no acreditan un mínimo global ni sustituyen la evaluación de márgenes y superficies funcionales. El visor resume las medidas y el agente recibe el informe completo. El protocolo obligatorio incorpora por separado la secuencia histórica de retenciones dual-mesh y distingue sus valores propuestos de los recuperados del laboratorio; una petición explícita posterior prevalece sobre el carácter opcional del vídeo.

Desde 0.5.10, las retenciones se restan con la herramienta protegida original acotada localmente; se evita restar caras que ya fueron recortadas contra la misma primaria. La aceptación prueba también la serialización y regularización numérica manteniendo los límites de componentes y topología. El centrado mide los intervalos de metal de la conexión, evitando confundir la otra rama de la arcada con un hombro. Solo las transiciones de código identificadas por hashes revisados conservan adaptadores anteriores; se reconstruye con las etapas y verificadores actuales, nunca con sus resultados antiguos.

Los diagnósticos independientes se ejecutan también cuando existe geometría medida completa pero falla su control final; la excepción original sigue fallando y los informes se conservan para corregir. No se prolonga una ejecución cancelada. Durante la construcción, el visor muestra los cambios del PLAN vigente en lugar de los ajustes iniciales del parser ya sustituidos; los datos iniciales permanecen en los informes.

La actividad se ve en **Ver construcción → Actividad del agente**. `Agente/Estado.json`, planes, revisiones, eventos, fuentes y diagnósticos forman parte de los resultados privados. Los eventos muestran acciones y conclusiones, no razonamiento interno.

Integración basada en el [modo no interactivo oficial de Codex](https://learn.chatgpt.com/docs/non-interactive-mode) y el [sandbox de Windows](https://learn.chatgpt.com/docs/windows/windows-sandbox), consultados el 10/09/2026.
