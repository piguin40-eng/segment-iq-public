# API local para el agente especialista

Base `http://127.0.0.1:8765`. Autenticación `Authorization: Bearer CLAVE_LOCAL`, leída del campo `password` de `data/config.local.json` sin imprimirla. Esta clave API se conserva al cambiar la contraseña web. Desde navegadores, `POST /login` recibe `username` y `password` y genera una cookie HttpOnly/SameSite Strict; operaciones con origen distinto se rechazan. Ver [acceso](ACCESO.md).

| Método y ruta | Entrada / uso |
|---|---|
| GET /api/status | Estado de modelos y biblioteca |
| POST /api/upload | Multipart `file`, vídeo/documento/STL; hasta 8 GB por subida |
| GET /api/search?q=... | Recuperación con fuente, tipo, segundo y captura |
| POST /api/chat | JSON `question`; respuesta y citas |
| GET /api/sources | Fuentes y estado de indexación |
| POST /api/sources/{id}/reindex | Encolar nuevo índice de esa fuente |
| POST /api/cases | Nombre y source_id del STL bruto; devuelve id y job_id y encola preparación y geometría |
| POST /api/cases/{id}/plan | Medir STL y preparar plan con RAG; localizar perfil del mismo hash si existe |
| POST /api/cases/{id}/profile | API técnica heredada; almacena un perfil validado. El flujo automático vuelve a medir el STL |
| POST /api/cases/{id}/generate | Medir internamente y generar otra versión; 409 si ya hay una activa |
| GET /api/jobs | Cola y resultados |
| GET /api/jobs/{id}/files | Archivos de salida disponibles |
| POST /api/feedback | JSON `case_id` o `general`, `author`, `text`, `status`: correction/approved/rejected; opcionales `attachment_ids` (hasta 20 fuentes subidas) y `request_plan` (bool) |
| GET /api/feedback | Historial con adjuntos, ejecución asociada y `plan_id` de la revisión solicitada |

Para iterar: subir las capturas/archivos con `/api/upload`, conservar sus IDs y enviar la corrección con `attachment_ids` y `request_generation: true`. Devuelve `id` de la observación y `job_id` de la nueva revisión. `request_plan` requiere un caso concreto y una corrección/rechazo; las aprobaciones se guardan sin pedir un plan. Si ya hay un plan pendiente, devuelve 409 antes de guardar la corrección: se puede reintentar con `request_generation: false` para guardar y revisar después.

Cada plan conserva en `Historial_de_la_revision.json` qué observaciones existían al solicitarlo, qué fuentes entraron en el contexto limitado del modelo y qué adjuntos se utilizaron. Las correcciones de otros casos se excluyen del contexto de revisión. La operación prepara un plan y mantiene las mallas y el perfil existentes; adaptar el perfil y ejecutar Blender es una operación posterior.

Los archivos de entrenamiento no pueden ordenar al servicio que ejecute código. Desde 0.5, con `agent_harness: codex`, el endpoint de generación activa el ciclo descrito en [ARNES_CODEX.md](ARNES_CODEX.md): Codex puede adaptar código numérico de forma en el workspace del caso; el supervisor conserva las verificaciones del motor y ejecuta Blender. `/api/status` indica el proveedor activado y si el CLI está instalado; esto no certifica disponibilidad de cuenta. `/api/jobs/{id}/progress` incorpora `agent` con estado, intento y eventos reales.


Desde 0.3, feedback admite request_generation: true para guardar y generar en una transacción. request_plan conserva el análisis sin geometría; no enviar ambos. Cada generación guarda Historial_de_la_version.json y el perfil preparado automáticamente. La API de perfil heredada no es necesaria en el flujo del panel.

## Rediseño del mismo trabajo (0.3.1)

- POST /api/cases/{id}/redesign: encola una nueva segmentación con las correcciones guardadas del caso y generales, sin reenviar texto. Requiere al menos una observación de corrección/rechazo pertinente. Devuelve job_id y case_id. 409 si existe generación activa; 400 si no hay correcciones; 404 si el caso no existe. Conserva el origen y no crea otro caso ni duplica observaciones.
- GET /api/cases/{id}/versions: devuelve todas las ejecuciones de geometría de ese caso, ordenadas de más reciente a más antigua. Excluye análisis e indexaciones y no depende del límite de 100 de la cola general.
- Para escribir una corrección nueva y generar en una sola operación, sigue disponible POST /api/feedback con request_generation: true.
