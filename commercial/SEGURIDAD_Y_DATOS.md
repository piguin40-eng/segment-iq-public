# Seguridad y privacidad: evaluación inicial

Alcance: lectura del código 0.5.2 y desarrollo del cliente preview. No es una auditoría de penetración independiente. **La instalación del laboratorio no se ha cambiado.**

## Riesgos que impiden abrir el servidor actual a clientes externos

| Riesgo observado | Tratamiento antes de venta | Evidencia de cierre |
|---|---|---|
| Cuenta compartida por laboratorio | Identidades individuales, roles administrador/técnico/revisor, MFA administrativo y revocación | Ensayos de autorización, sesiones, recuperación y baja |
| LAN actual en HTTP | Cliente comercial solo HTTPS remoto; proxy correctamente configurado, origen/Host permitido, cookies seguras y CSRF | TLS, DNS rebinding, CSRF, proxy y micrófono probados |
| SQLite y archivos sin cifrado propio | Cifrado de disco administrado, permisos por cuenta, backup cifrado y claves separadas; revisar cachés, miniaturas, índices y exportaciones | Restauración probada y control de accesos; no afirmar cifrado solo por contraseña |
| Motor con código numérico editable por el agente | Cuenta de servicio/VM aislada, sin credenciales ajenas, montajes por caso, límites de CPU/RAM/disco/tiempo y salida de red restringida | Pruebas adversarias reales; AST y sandbox de Codex no aíslan automáticamente el código ejecutado después por Blender/Python |
| Uploads/documentos/vídeos no fiables | Límites antes de parsear multipart, cuotas, tipos reales, parser aislado y límites de archivo descomprimido | Ensayos de archivos malformados, agotamiento de disco y concurrencia |
| App monolaboratorio | Un motor y almacenamiento aislados por laboratorio; SaaS multicliente solo tras control de tenant en cada recurso/tarea | Pruebas cruzadas de acceso a casos, RAG, adjuntos, descargas y colas |
| Correcciones y nuevos ejemplos | Trazabilidad original → instrucciones → motor/modelo → propuesta → revisión; promoción explícita del patrón común | Dataset de evaluación versionado, criterios objetivos y rollback |
| Actualizaciones/cadena de suministro | Paquetes firmados, dependencias fijadas, SBOM y avisos de seguridad, aprobación de versiones | Instalación limpia, firma, manipulación, migración y recuperación probadas |
| Sesión de proveedor IA del laboratorio | No redistribuirla; cuenta/contrato comercial adecuado, segregación y presupuesto por cliente | Revisión de flujos, términos, subencargados y prueba sin secretos compartidos |

## Flujo y minimización de datos

Cliente de escritorio → servidor del laboratorio (casos, correcciones, audio). Servidor → Ollama/modelos locales para RAG según configuración. **El arnés Codex existente puede enviar geometría, imágenes, textos y rutas al proveedor de IA.** “Local” no debe usarse en marketing como garantía de que ningún dato sale. La preview no cambia ese comportamiento del servidor.

Objetivo del futuro servicio de suscripciones: únicamente identificador de organización/dispositivo, producto, fechas, plan, estado de pago y datos fiscales necesarios. Ni STL ni voz son necesarios para comprobar una suscripción. Telemetría y soporte no deben enviar automáticamente casos o volcados con datos personales. Nombres de archivo, capturas, vídeos, logs y embeddings pueden contener datos de salud incluso si no aparece el nombre del paciente.

En UE documentar responsable/encargado y subencargados, base del artículo 6 y condición del artículo 9 cuando corresponda, contratos de encargo, medidas técnicas, transferencias internacionales, plazos, derechos, incidentes y evaluación de impacto cuando proceda. No usar una casilla de consentimiento genérica como solución universal. Referencia: [AEPD, datos de salud](https://www.aepd.es/areas-de-actuacion/salud/tus-derechos-en-relacion-con-tus-datos-de-salud).

En EE. UU. determinar si somos business associate según el servicio y acceso a PHI. Vender software sin acceso no equivale automáticamente a esa condición; soporte o nube que accede a PHI puede cambiar el análisis. No anunciar “certificado HIPAA” por añadir cifrado. Fuente: [HHS, proveedores de software](https://www.hhs.gov/hipaa/for-professionals/faq/256/is-software-vendor-business-associate/index.html). Canadá, México, Brasil y demás mercados requieren su análisis de datos y transferencias separado.

## Comportamiento de la suscripción ante incidencias

Sin licencia vigente, conservar lectura/exportación de trabajos previos y la posibilidad de recuperar datos. Si una generación ya empezó con licencia válida, no cortar Blender a mitad por un fallo temporal de cobro; comprobar al encolar y al arrancar, registrar y aplicar una política documentada. Definir gracia firmada para caídas del servicio, caducidad y revocación. No borrar expedientes como sanción por impago.

## Prueba de salida mínima

Revisión de acceso/aislamiento y prueba independiente; restauración de backup; simulación de actualización fallida; dependencias/SBOM y vulnerabilidades; registro de incidentes y responsable de respuesta; cierre de defectos geométricos que afecten a la finalidad prevista. Ensayar datos sintéticos o legítimamente autorizados. El historial actual de propuestas aún conserva comprobaciones globales de espesor, inserción y resistencia pendientes: deben cerrarse antes de prometer fabricación clínica fiable.
