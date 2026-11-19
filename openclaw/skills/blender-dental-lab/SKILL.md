---
name: blender-dental-lab
description: Consultar el RAG audiovisual del laboratorio, incorporar puentes terminados como referencias de diseño, recuperar correcciones por caso y construir segmentaciones primaria/supra propias en Blender a partir de STL bruto.
---

# SEGMENT IQ

Para coronas o pilares sobre implantes y modelos con análogos, consultar [blender-implantes-protesis](references/blender-implantes-protesis/SKILL.md) y ambas referencias antes de preparar y revisar. Recuperar `LAB-IMPLANTES-PROTESIS-20260916` en el RAG. Mantener los implantes ya alineados por el laboratorio, distinguir conexión protética de alojamiento de análogo y conservar las superficies funcionales. La incorporación del tutorial externo no demuestra que el motor haya ejecutado sus operaciones.

Para diseñar o corregir anatomías, posicionamiento, arcada, contactos y oclusión antes de segmentar, leer [blender-diseno-dental](references/blender-diseno-dental/SKILL.md) y sus referencias. Recuperar `LAB-DISENO-DENTAL-20260916` en el RAG. Incluye criterios del laboratorio y una síntesis documental de Encerados, parte 2; no atribuir al tutorial la aprobación del laboratorio ni confundir esta incorporación con un motor nuevo de encerado. Esta carpeta viaja con la skill a cada espacio de trabajo del arnés.

Para toda segmentación de barra, leer obligatoriamente [blender-barras-video](../blender-barras-video/SKILL.md), su procedimiento y evidencia temporizada. El supervisor carga ese contenido en PLAN y REVIEW y exige respuesta por etapa con hash de versión; no depende del ranking del RAG. Las notas posteriores del laboratorio siguen teniendo prioridad. La skill documenta el vídeo y sus límites; no amplía por sí sola las operaciones B4D disponibles.

Criterio permanente de el laboratorio del 16/09/2026: primaria recta, sin socavaduras, más estrecha y con menos espesor de metal para preservar el contorno de la secundaria. Leer [barra recta y trayectoria de inserción](references/barra-recta-sin-socavaduras.md) y recuperar `LAB-BARRA-RECTA-20260916` con sus capturas. Aplicar todas las exigencias juntas, protegiendo conexiones; comparar anchura, altura, perfil y extracción con la versión anterior. No sumar dos reducciones por la misma nota guardada en ámbito general y de caso. No afirmar cumplimiento sin una nueva geometría y controles específicos; la incorporación del criterio no implementa por sí sola un control universal de socavaduras.

Para fosas oclusales, chimeneas anguladas y resultados asistidos importados, leer [fosas, canales y revisión](references/fosas-canales-angulados-revision.md) y recuperar `LAB-SEG-3U-FOSAS-20260915`. La ejecución preserva su estado pendiente de revisión y el código privado del caso; indexarla no actualiza el detector automático general ni convierte su barra en un acabado aprobado.

Para referencias de anatomía, cuellos y encía de puentes sobre implantes, leer [referencia de tres piezas](references/puente-tres-piezas-referencia-lab.md) y recuperar `LAB-PUENTE-3U-20260915` en el RAG. El puente terminado 14–15–16 del laboratorio es la referencia morfológica; nuestra v009 con collares de encía fue rechazada. Comprobar el registro rígido antes de superponer el STL con los escaneos. El original conserva su geometría y autoría; guardar esta evidencia no entrena pesos ni identifica por sí solo materiales, pasos B4D o aprobación de fabricación.

Desde 0.5, si `agent_harness` es `codex`, la generación incorpora el ciclo de interpretación, herramientas, edición de adaptadores de forma, ejecución Blender, comprobación y revisión visual. Leer [arnés y límites](../../../docs/ARNES_CODEX.md). Seguir la misma ejecución y su campo `agent` en `/api/jobs/{id}/progress`; no repetir la petición desde otro agente. Los adaptadores aceptados se conservan solo para ese caso y versión del motor, sin promoción automática al resto de pacientes. Las notas, imágenes y medidas usadas para razonar pasan por Codex; el chat de biblioteca sigue con Ollama local.

Desde 0.4.5, consultar también la sección de terminación, crestas y afinado de [correcciones geométricas](../../../docs/CORRECCIONES_GEOMETRICAS.md). Recuperar las notas y abrir sus capturas antes de adaptar una operación pendiente. No confundir «sin cambios interpretados» con una corrección realizada: mantener la propuesta previa. Evitar duplicar una misma nota guardada a la vez como criterio general y corrección del caso. El bisel y afinado sin cotas son propuestas medidas que requieren revisión; las marcas 2D no son por sí solas una curva 3D.

Cuando el técnico pida centrar las conexiones o reducir metal para proteger la supra, leer [correcciones geométricas](../../../docs/CORRECCIONES_GEOMETRICAS.md). Desde 0.4.4 cada indicación se interpreta por separado, se compara con la versión anterior y se exige cambio geométrico real. Medir el centrado en los hombros de barra a ambos lados de cada eje; un collar circular conservado no basta. Una reserva oclusal favorable tampoco descarta ventanas laterales: revisar la topología de ambas piezas y la seguridad local. La altura pedida para otro caso no prevalece sobre una reducción expresa en el actual.

Desde 0.4, seguir `/api/jobs/{id}/progress` y el visor «Ver construcción»: contiene vistas reales de etapas terminadas, errores e indicaciones pendientes. No describirlo como grabación de ratón ni atribuir etapas a B4D sin recibo. La integración local ejecuta actualmente **solo la herramienta de cemento de iBar**; comprobar `B4D_ejecucion.json` con PASS y conservar su hash/parámetros. La construcción restante es SEGMENT IQ. Leer `docs/VISOR_Y_B4D.md` antes de configurar ese adaptador; no distribuir el complemento propietario.

Las notas mixtas de altura anterior y espesor se desglosan. El TOP regional se mide por anatomía y se comprueba la altura resultante en `design_sections`. El espesor oclusal muestreado **no acredita el mínimo global de 0,8 mm** en paredes laterales/márgenes; esa exigencia permanece pendiente hasta un control completo. Mostrar la parte aplicada y la pendiente por separado. No borrar otras instrucciones regionales de la misma observación.

Desde 0.4.1 revisar `Seguridad_oclusal_local.json` para la corrección automática de intervalos oclusales finos. Comprueba material continuo a cada lado de los huecos de chimeneas; no usar solo máximo/mínimo de Z. La herramienta modifica localmente el separador y vuelve a proteger las conexiones. Exigir mejora medida antes/después; si se detiene sin resolver, conservar el fallo y no darlo por corregido.

El laboratorio exige segmentar tanto conexiones sobre interfases como directas a implante: localizar la chimenea y proteger todo el perímetro de la región funcional del STL. Desde 0.3.2 el detector agrupa ejes y paredes verificadas, admite puentes cortos y añade protección después del remallado/cemento y frente a retenciones. Usar el motor actualizado; no recuperar la exigencia antigua de tres asientos ni pedir JSON o una clasificación comercial. Revisar `functional_connection_protection` antes y después de exportar: volumen conservado, distancia de superficie y eje libre. No afirmar conservación por comprobar solo el anillo, ni dar por aplicada una corrección que figure pendiente.

Desde 0.3, crear un caso por la API encola medición y geometría automáticamente: usar el `job_id` devuelto y seguirlo hasta terminar. No pedir JSON al técnico ni encolar una segunda generación inmediata. `engine/prepare_profile.py` mide el STL y propone el perfil; leer `docs/PREPARACION_AUTOMATICA.md` para sus límites. Para iterar con geometría enviar feedback con `request_generation: true`; `request_plan` produce solo análisis. Conservar las indicaciones no aplicadas como pendientes, sin afirmar que una captura ya modificó una región. No dar por aprobado un diseño por superar controles.

El servicio local del laboratorio proporciona un RAG con transcripciones, OCR, descripciones de capturas y referencias de tiempo. Las descripciones del modelo y transcripciones están sin revisar; las correcciones del técnico llevan ámbito y fecha. Citar las fuentes y abrir la captura/vídeo cuando la decisión dependa de un movimiento o valor visible. Un fotograma aislado no demuestra una secuencia ni el estado de selección de Blender.

En la instalación Windows predeterminada, el código está en `%USERPROFILE%/Documents/DentalLabAgent/app` y el Python del agente en `../runtime/python/Scripts/python.exe`. Ejecutar desde la carpeta app:

```text
../runtime/python/Scripts/python.exe -m dental_lab.cli search "seguridad barra inferior"
../runtime/python/Scripts/python.exe -m dental_lab.cli ask "Explica el patrón de retenciones y cita las fuentes"
../runtime/python/Scripts/python.exe -m dental_lab.cli index "D:/Aprendizaje/video.mp4" --queue
```

Consultar `docs/API.md` para gestionar casos, planes y ejecuciones por la API local. Usar la clave de configuración local como Bearer en el cliente, sin imprimirla ni guardarla en Git. El panel permite revisión de resultados y correcciones; el agente no debe registrar aprobaciones en nombre del técnico.

Antes de segmentar: leer `docs/PROCESO.md`; registrar STL bruto, hash, orientación y medidas del caso. Consultar fuentes relevantes, reconstruir perfiles y herramientas propios, adaptar el código y comprobar etapas. No importar perfiles/cutters/retenciones de los .blend terminados como geometría de salida. El perfil de referencia solo corresponde a su archivo identificado por hash. No tomar ocho conexiones, radio 2,4 o gap 0,14 como universales.

Construir en el orden: orientación → tubos/conos → trazado → diseño básico → remallado → seguridad → cemento → separación → retenciones → validación/exportación. No sustituir más altura de barra por aumentar globalmente la escala ni bajar todo el diseño. Incluir los extremos distales completos (37 en el caso documentado), aunque no tengan implante.

El código disponible en `engine/` produce escenas, STL, logs y métricas. Para geometría usar el Python independiente `runtime/geometry-python/Scripts/python.exe`. Las etapas que no replican literalmente B4D deben quedar identificadas. Si los controles fallan, corregir la causa, no relajar umbrales para forzar PASS.

Entregar planos/escenas y medidas que permitan revisar altura, profundidad, asiento y anatomía. Una malla cerrada con topología correcta no demuestra espesor mínimo ni ajuste de fabricación. Diferenciar propuesta, geometría comprobada y aprobación expresa del laboratorio.
