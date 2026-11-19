# Preparación comercial de SEGMENT IQ

**Fecha de revisión: 11 de septiembre de 2026. Estado: preparación; no autorizado como producto comercial terminado.** Mercados solicitados: España, UE y América. Modelo: aplicación de escritorio con suscripción B2B para laboratorios.

## Lo preparado

Cliente de escritorio separado, instalador Windows de evaluación y automatización de compilación macOS Intel/Apple Silicon. Conecta con el panel existente del laboratorio. No se ha modificado ni actualizado la aplicación en funcionamiento, su acceso, sus casos, sus credenciales o su servicio. El trabajo comercial se conserva en la rama `commercial/desktop-readiness`; no debe fusionarse ni desplegarse sobre el laboratorio sin un ensayo de migración.

La preview ofrece conexión y acceso, no ejecuta el motor localmente en Mac. Tampoco cobra suscripciones, emite licencias comerciales, instala Blender/B4D ni obtiene permisos sanitarios. Estos puntos se distinguen expresamente en la documentación para evitar promesas que el prototipo aún no puede cumplir.

## Modelo de producto propuesto

| Parte | Diseño objetivo | Situación real |
|---|---|---|
| Escritorio | Instalador por sistema, acceso sencillo, archivos, correcciones y dictado | Cliente preview añadido; usa el panel actual |
| Motor de laboratorio | Una instalación y cuenta de servicio aisladas por laboratorio | Motor Windows actual; aislamiento comercial por reforzar |
| Cuenta/suscripción | Organización, miembros, permisos, dispositivos y facturación | Especificado, no implementado ni cobrado |
| Licencia | Verificada por el servidor antes de encolar/ejecutar; nunca solo en el cliente | Especificada; aplicación actual sin cambios |
| Datos | Casos en el laboratorio; nube comercial recibe solo datos de licencia y facturación | Objetivo; arnés Codex actual puede enviar datos del caso al proveedor |
| RAG | Biblioteca privada por laboratorio y catálogo común de material autorizado | Memoria local existente; no reentrena pesos automáticamente |
| Distribución | Página HTTPS con enlaces a instaladores firmados, versión y hashes | Sin dominio comercial ni firma configurados |

El escritorio y el motor tienen versiones independientes. Un cliente Mac puede usar un motor Windows de su laboratorio. No prometer “cualquier ordenador”: comprobar versiones de SO, arquitectura, memoria, GPU cuando proceda, B4D y tamaños máximos con pruebas reproducibles. Objetivo inicial de cliente: Windows 11 x64 y macOS 14 o posterior, Intel/Apple Silicon sujeto a matriz de pruebas. Windows ARM y motor nativo macOS quedan fuera de lo validado.

## Secuencia para abrir ventas

1. Definir titular, finalidad prevista, países concretos y alcance del producto. Solicitar dictamen de clasificación sanitaria y revisar derechos de todo el código, plugins y corpus. No asumir que la certificación de un componente cubre el producto propio.
2. Cerrar la validación del motor: preservar conexiones, espesor global, inserción, retenciones, márgenes, unidades, coordenadas, reproducibilidad y revisión humana. Que una malla sea cerrada no demuestra que se pueda fabricar ni que resista.
3. Aislar y asegurar cada servidor; introducir identidad por persona, roles, auditoría, backup/restauración, cifrado y permisos. Ensayar corpus malicioso, abuso de uploads, límites de CPU/memoria y ejecución de código del agente.
4. Implementar el servicio de suscripciones y probar su integración en una copia de ensayo. Cancelación y caducidad deben conservar acceso a los archivos previos. Las actualizaciones nunca reinician una generación en curso.
5. Contratar cuentas/certificados del titular, firmar Windows y notarizar Mac; probar instalación/actualización/desinstalación en máquinas limpias de cada arquitectura. Publicar descargas por HTTPS solo para los mercados aprobados.
6. Abrir piloto y ventas con contratos, soporte, procedimiento de incidentes y control de cambios. Revisar la aplicabilidad de los requisitos regulatorios incluso en pilotos: la palabra “beta” no exime por sí sola.

## Documentos de trabajo

- [Mapa de permisos y países](REGULACION_Y_DERECHOS.md).
- [Seguridad, privacidad y riesgos](SEGURIDAD_Y_DATOS.md).
- [Suscripción, instalación y contratos](SUSCRIPCION_Y_ENTREGA.md).
- [Registro de requisitos pendientes](release-readiness.json), comprobable con `python commercial/check_readiness.py`.
- [Solicitud preparada para asesores y proveedores](SOLICITUDES_PENDIENTES.md). No se ha enviado ningún mensaje ni firmado contrato.

El registro de salida es un control interno de evidencias, no una certificación jurídica ni una garantía de seguridad. Actualmente debe devolver **BLOQUEADO PARA VENTA**. No rellenar aprobaciones por haber ejecutado pruebas de software.
