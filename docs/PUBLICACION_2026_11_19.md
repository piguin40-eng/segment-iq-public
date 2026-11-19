# Verificación de la copia pública

Se reúnen el servidor/motor 0.5.25 y el cliente Desktop 0.6.0-preview.1. El servicio del laboratorio permanece separado y no se reinstala por publicar esta copia.

- 261 pruebas Python aprobadas, incluyendo preparación, recuperación, geometría, exportación, biblioteca, API y criterios de preparación comercial.
- Pruebas Node aprobadas: tres de política del cliente y siete escenarios del dictado.
- Archivos preparados revisados para excluir formatos de casos, configuraciones, credenciales y datos privados. La publicación tiene un historial nuevo de código.
- Los archivos inmutables del motor conservan sus bytes entre plataformas para mantener los hashes de sus migraciones revisadas.
- Ambos DMG Mac coinciden por SHA-256 con las compilaciones previamente registradas y con sus archivos ZIP originales. El código empaquetado de `desktop/src`, sus dependencias y la configuración de compilación coinciden con el cliente incluido; la prueba de humo añadida después no cambia el paquete. Ver `desktop/BUILD_PROVENANCE.json`.

Estas pruebas no incluyen una ejecución de segmentación nativa en Mac ni una instalación en hardware Mac. Los DMG siguen siendo previews sin firma/notarización del titular. El motor conserva sus controles y pendientes de validación; la publicación no aprueba casos para fabricación ni completa los requisitos comerciales.
