# Descargar SEGMENT IQ en un Mac

## Guardar el proyecto completo

Abre [la descarga ZIP del proyecto](https://github.com/piguin40-eng/segment-iq-public/archive/refs/heads/main.zip). Haz doble clic en el ZIP y conserva la carpeta descomprimida. Incluye servidor, motor, interfaz, RAG, skills, cliente de escritorio, pruebas y documentación.

También puedes usar Git:

```bash
git clone https://github.com/piguin40-eng/segment-iq-public.git
```

Esta copia pública no contiene tu biblioteca privada, los casos, las contraseñas ni las licencias de terceros. Para trasladar el conocimiento real y los expedientes se necesita además una transferencia privada del directorio de datos; no subirlo a este repositorio.

## Abrir el cliente Mac

En [Descargas](https://github.com/piguin40-eng/segment-iq-public/releases/tag/v0.5.25-public.1), elige:

- `mac-arm64.dmg`: Mac con chip Apple (M1, M2, M3, M4 o posteriores compatibles).
- `mac-x64.dmg`: Mac con procesador Intel.

Puedes consultar el chip en el menú Apple → Acerca de este Mac. Abre el DMG y copia SEGMENT IQ Preview a Aplicaciones. La preview no está firmada ni notarizada por el titular; macOS puede impedir su apertura. No desactives globalmente las protecciones del sistema.

Introduce la dirección HTTPS de tu servidor del laboratorio e inicia sesión con la cuenta de esa instalación. El cliente exige un certificado válido para otro ordenador y no convierte la red HTTP existente a HTTPS. El servidor debe permanecer encendido y accesible desde el Mac. Si solo tienes acceso LAN por HTTP, puedes abrir el panel en el navegador de tu Mac dentro de esa red; el dictado por micrófono requiere HTTPS.

El cliente muestra la aplicación y descarga sus resultados, pero la segmentación sigue ejecutándose en el servidor Windows. **No es todavía un instalador del motor Blender/B4D para ejecutar todo localmente en el Mac.**

## Compilar el cliente desde el código

En un Mac con Node.js 24 y pnpm 11.19.0:

```bash
cd segment-iq-public/desktop
pnpm install --frozen-lockfile
node node_modules/electron/install.js
pnpm test
pnpm exec electron-builder --mac --arm64 --publish never
```

Usa `--x64` en lugar de `--arm64` para Intel. El paquete se guarda en `desktop/dist/`. La compilación no añade firma ni notarización automáticamente. Los archivos de terceros conservan sus licencias.
