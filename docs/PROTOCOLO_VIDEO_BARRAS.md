# Protocolo obligatorio del vídeo de barras

SEGMENT IQ 0.5.3 carga `openclaw/skills/blender-barras-video/` desde la instalación. No depende de que la búsqueda RAG lo sitúe entre sus primeros resultados. La versión 1.0.0 sintetiza el vídeo que el laboratorio indicó como patrón; procedimiento, tiempos, valores observados y límites se encuentran en la skill.

En el arnés Codex, `prepare` comprueba que existen los tres documentos y conserva una copia por trabajo. `think` inyecta el contenido completo en cada PLAN y REVIEW. El esquema de respuesta exige `lab_workflow.sha256` y diez etapas, cada una con estado, explicación y evidencia. Se rechazan versiones distintas, omisiones, duplicados, estados inaplicables y etapas marcadas como comprobadas sin evidencia. Las etapas pendientes pasan a la lista visible de pendientes del resultado. Los archivos se conservan en `outputs/Agente/Protocolo_obligatorio/`, las respuestas en los registros de planificación/revisión, y el resumen en `Contexto_del_agente.json` y `Preparacion/Perfil_automatico.medidas.json`.

Esto acredita suministro de instrucciones y respuesta estructurada. No demuestra que el modelo diga la verdad sobre cada medición, que todas las operaciones del vídeo estén implementadas, ni que haya pasado una comprobación clínica. Los verificadores geométricos siguen siendo independientes y no se han modificado. El adaptador B4D instalado continúa ejecutando solo la operación de cemento; las demás etapas propias deben identificarse como SEGMENT IQ y justificarse o quedar pendientes.

El motor fijo, si se selecciona expresamente en la configuración, conserva la referencia y deja pendiente su revisión: no interpreta instrucciones nuevas de una skill. La instalación del laboratorio usa `agent_harness=codex`. El análisis de biblioteca conserva el protocolo y recibe su entrada principal, pero no se presenta como generación de geometría.

La pantalla Criterio del laboratorio muestra disponibilidad/versión y descarga la skill con sus referencias. `/api/lab-workflow` y `/api/lab-workflow/download` están autenticados. La descarga contiene únicamente los tres Markdown: excluye vídeo, datos de pacientes y B4D. Los accesos directos y la URL de la app no cambian.

El vídeo y las diez síntesis contrastadas permanecen en la base privada, con tiempo y fotograma. Reindexar el vídeo reemplaza la transcripción/OCR automáticos pero conserva las síntesis contrastadas. Cada instalación puede tener distinto source_id; la identificación estable del vídeo usa SHA-256. Importar otros vídeos en biblioteca no los convierte automáticamente en nuevas reglas obligatorias.

Para actualizar el patrón, modificar las referencias, revisar evidencia y aumentar `VERSION` en `dental_lab/lab_workflow.py`; el hash recoge contenido y lista de etapas. Las ejecuciones ya iniciadas mantienen su copia. No reescribir recibos de resultados antiguos para aparentar que ya siguieron el protocolo nuevo. Distribuir la carpeta de skill con el código de la app, y usar una instalación B4D licenciada cuando corresponda.

Verificación: `tests/test_lab_workflow.py`, junto con pruebas de arnés, creación/iteración de casos, API y resultados. No se ha regenerado un caso clínico solo para instalar esta skill.
