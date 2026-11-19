# SEGMENT IQ Desktop — preparación comercial

**0.6.0-preview.1. Evaluación interna.** Cliente nativo para el servidor SEGMENT IQ existente. La aplicación instalada del laboratorio no se modifica. Esta carpeta no incorpora el motor dental, cuentas, suscripciones activas ni expedientes. Compilar un cliente para Mac no valida el motor local en Mac.

## Uso de la preview

1. Instalar el paquete de prueba en un entorno de evaluación. En Windows crea **SEGMENT IQ Preview**, separado de SEGMENT IQ. No requiere administrar el sistema ni cambia el firewall, el servicio o los datos del laboratorio.
2. Introducir la dirección del servidor. En este ordenador, `http://127.0.0.1:8765`. En otro equipo, un servidor HTTPS con certificado válido. La preview no convierte automáticamente la instalación LAN HTTP existente a HTTPS.
3. Se comprueba `/health` y se abre el panel existente. Iniciar sesión con la cuenta de ese laboratorio. Los casos permanecen en su servidor; las descargas que el usuario guarde sí quedan en el equipo cliente.
4. El dictado pide permiso para audio; cámara y pantalla están denegadas. Al cerrar, la sesión del cliente se limpia. El único ajuste persistente es la dirección del servidor.

Desinstalar la preview no desinstala el servidor ni borra casos. Si el servidor está apagado, debe arrancarlo el responsable del laboratorio: este cliente no crea ni arranca motores en otro equipo.

## Compilación reproducible del cliente

Node.js 24 y pnpm 11.19.0. Dependencias directas fijadas y árbol con integridades en `pnpm-lock.yaml`. Revisar las versiones y avisos de seguridad de nuevo antes de cada publicación.

```text
pnpm install --frozen-lockfile
node node_modules/electron/install.js
pnpm test
pnpm run dist:win
pnpm run dist:mac -- --x64
pnpm run dist:mac -- --arm64
```

Compilar macOS en macOS. `desktop-preview.yml` prepara artefactos de evaluación para Windows x64 y macOS x64/arm64 sin publicar releases. Los artefactos sin firma no son distribución comercial. No instruir a clientes para desactivar SmartScreen o Gatekeeper.

Electron viene en el paquete; no hace falta instalar Node ni Python en el ordenador cliente. **Sí hace falta un servidor configurado.** El motor actual sigue dependiendo de Python, Blender 3.6/B4D y su licencia en Windows. No se incluyen sus binarios en esta preview.

## Seguridad implementada en el cliente

Contenido remoto sin Node ni puente IPC; sandbox y context isolation activados. Conexión HTTPS salvo IP loopback literal. Validación de certificados predeterminada, sin excepciones. Orígenes, navegación y ventanas emergentes restringidos. No se admiten claves en la URL ni direcciones con rutas o parámetros. El formulario local usa un protocolo propio y CSP restrictiva. IPC limitado al formulario local de la ventana principal. Sesiones en memoria; no se copian credenciales del laboratorio.

Esto no convierte el servidor actual en SaaS multicliente ni en una frontera segura para ejecutar código arbitrario. Ver el [expediente comercial](../commercial/LEEME.md), especialmente el aislamiento del motor, la protección de datos y las pruebas pendientes. Las páginas servidas y los ficheros descargados siguen necesitando sus controles propios.

## Distribución estable pendiente

El canal estable necesitará titular legal, certificados de firma, notarización Apple, HTTPS para los motores, derechos de integración, validación sanitaria y suscripción verificada en servidor. La app actual no se migra automáticamente a este esquema. No hay autoactualizador activo ni URLs de cobro ficticias.
