# Suscripción y distribución — especificación para implementación

**Estado: diseño de integración, no facturación activa.** No cambia los accesos ni la generación del laboratorio actual.

## Experiencia objetivo

Un enlace HTTPS muestra instalador Windows y Mac según arquitectura, versión, requisitos, avisos y notas de versión. El laboratorio se registra, contrata y recibe su organización y servidor provisionado. Descarga y abre SEGMENT IQ, inicia sesión y selecciona su laboratorio. Si requiere motor local, un asistente independiente comprueba hardware, Blender/B4D y licencias. El cliente de escritorio por sí solo no instala ese motor.

El canal de descarga debe ser público o autenticado de forma apropiada; un enlace de un repositorio GitHub privado exige autorización y no es aún un enlace comercial universal. Un repositorio privado de código debe seguir separado del bucket/CDN de instaladores. No publicar código privado ni casos para hacer funcionar una descarga.

## Entidades y contrato de licencia

Organización (`tenant_id`), personas y roles, instalación de motor (`installation_id` aleatorio), dispositivos, suscripción, concesión de licencia, eventos de cobro e historial de auditoría. Secretos en el servidor/vault, nunca en JavaScript del cliente. Guardar credenciales del usuario mediante flujos y almacenes del SO apropiados cuando se implemente persistencia.

El proveedor de pagos elegido debe enviar webhooks firmados. Verificar firma sobre el cuerpo crudo, límite temporal y tamaño, identificar el evento y procesarlo de forma idempotente/transaccional. No conceder licencia por volver a una página de “pago correcto”, por valores que envíe el escritorio ni por estados de pago fuera de orden. Consultar el estado canónico del proveedor al reconciliar. Los precios, impuestos, divisa y plan los decide el backend; quedan por aprobar, sin cobrar desde esta preparación.

Una concesión de licencia firmada puede incluir emisor, audiencia, identificador, organización, instalación, capacidades, emisión, inicio y vencimiento UTC, identificador de clave y versión de formato. Verificar firma con claves públicas confiables, esquema estricto, algoritmo fijo, audiencia y vinculación de instalación; contemplar rotación, reloj manipulado, revocación y recuperación. La clave privada de emisión nunca se distribuye. Una licencia offline limita dependencia de red pero retrasa revocaciones: documentar la gracia y su riesgo. No afirmar que es imposible de manipular para el administrador del equipo.

El motor debe comprobar la licencia al encolar y antes de empezar la generación, también en trabajos heredados y solicitudes directas a la API. Un botón oculto en el cliente no impone una suscripción. La lectura, correcciones conservadas y exportación anterior siguen disponibles según contrato al terminar la suscripción.

## API prevista (aún no existe)

| Operación | Controles |
|---|---|
| Registro/invitación de miembros | Verificación de correo, pertenencia, rol, caducidad, límites de intentos |
| Sesión/renovación/cierre | Cookies/tokens limitados, rotación y revocación, MFA para administración |
| Crear checkout / portal de cliente | Usuario administrador de su tenant; planes permitidos definidos en servidor |
| Webhook de cobro | Firma del proveedor, idempotencia, reconciliación, sin confiar en redirecciones |
| Activar/desactivar motor | Identidad de instalación y límite de plazas; no MAC/hardware biométrico invasivo |
| Renovar licencia | Estado canónico del pago, contrato, país habilitado y versión compatible |
| Descargar versión | Manifiesto de versión, firma, hash y compatibilidad; URL temporal cuando proceda |

## Documentos contractuales que deben aprobarse

- Condiciones B2B/EULA: titular, finalidad y alcance, número de puestos/motores, plugins separados, duración, renovación, baja, exportación, soporte, SLA y límites de responsabilidad revisados por asesoría.
- Privacidad y encargo de tratamiento/DPA; BAA cuando corresponda; lista de subencargados, transferencias y soporte remoto.
- Derechos sobre aprendizaje: materiales propios/autorizados, biblioteca privada, aportación opt-in al catálogo común, retirada y derechos de terceros.
- Política de soporte, mantenimiento y cambios del motor; vulnerabilidades e incidentes; compatibilidad del software y de B4D.
- Información fiscal, facturación, IVA/inversión del sujeto pasivo/otros impuestos según cliente y país. Que el negocio sea suscripción no resuelve automáticamente impuestos internacionales.

No se han redactado condiciones definitivas a nombre de una sociedad desconocida ni contratado un proveedor de cobro.

## Publicación y actualizaciones

Mantener canales preview/estable independientes. El workflow incluido compila previews y guarda artefactos privados; no publica una release estable. La firma se añade solo con certificados del titular mediante secretos protegidos y entornos de release con revisión. Para Mac: compilar, firmar, notarizar, adjuntar ticket y verificar Gatekeeper. Para Windows: firmar binarios e instalador, sello de tiempo, verificar en máquina limpia. Los hashes permiten comprobar integridad del archivo recibido pero no sustituyen la firma.

Autoactualización pendiente: canal autenticado/firmado, rechazo de downgrade y firma incorrecta, política de rotación y recuperación. No descargar/ejecutar scripts arbitrarios desde una URL ni desactivar verificaciones TLS. El motor debe actualizarse de forma coordinada y tras drenar su cola, con copia de seguridad y rollback de esquema. La aplicación en uso del laboratorio se mantiene tal como está hasta una migración revisada.
