# SEGMENT IQ local en Mac Apple Silicon

Esta instalación ejecuta el servidor, el motor geométrico con Blender, la biblioteca RAG y la transcripción en el Mac. No necesita tener encendido ni conectado el Windows del laboratorio. El agente de correcciones utiliza Codex y requiere Internet y tu propia cuenta compatible; no es una instalación de IA completamente desconectada.

## Instalar

Requisitos: Mac con chip Apple Silicon, macOS 14 Sonoma o posterior y espacio para varios GB de aplicaciones/modelos más los casos. Recomendamos reservar al menos 20 GB y disponer de 16 GB de memoria para trabajar con Blender y el modelo visual. El instalador comprueba sistema y arquitectura; no utiliza Rosetta.

1. Descarga [SEGMENT-IQ-Mac-local-0.6.0.zip](https://github.com/piguin40-eng/segment-iq-public/releases/download/v0.6.0-mac-local.1/SEGMENT-IQ-Mac-local-0.6.0.zip) y descomprímelo.
2. Dentro de la carpeta, abre **Instalar-SEGMENT-IQ-Mac.command**. Si macOS bloquea el archivo descargado, revisa su procedencia y permite únicamente ese archivo mediante los controles de Privacidad y seguridad; no desactives Gatekeeper. Este paquete aún no tiene firma/notarización comercial.
3. Crea tu usuario y contraseña locales. Espera a que se descarguen los componentes y modelos. La primera preparación puede tardar bastante según tu conexión.
4. Cuando se abra el inicio de sesión de Codex, entra con tu propia cuenta. No necesitas copiar contraseñas ni tokens del Windows.
5. Abre **SEGMENT IQ Local** en la carpeta **Aplicaciones de tu usuario** (`~/Applications`). El panel aparece en `http://127.0.0.1:8765` y utiliza el usuario creado en el paso 3.

La contraseña no se muestra mientras la escribes en Terminal. La instalación debe terminar con «SEGMENT IQ local preparado». Si aparece «INSTALACION INCOMPLETA», conserva el mensaje: no equivale a una instalación terminada. Puedes repetir el instalador; conserva tus datos y cuenta. No actualices mientras haya trabajos activos.

## Qué instala y dónde

Todo queda en `~/Library/Application Support/SEGMENT IQ/`:

| Ruta | Contenido |
|---|---|
| `app/` | Código completo, interfaz, motor y skills |
| `runtime/` | Python, entornos aislados, Blender 3.6.23 arm64, Ollama y Codex |
| `data/` | Cuenta local, casos, correcciones, índices y modelos privados |
| `data/logs/` | Registros de arranque y compatibilidad |
| `INSTALLATION.json` | Estado de preparación, sin contraseña ni token |

Dos servicios del usuario se registran en `~/Library/LaunchAgents/`: `com.segmentiq.local` y `com.segmentiq.ollama`. Arrancan al iniciar sesión. Solo escuchan en el propio Mac; el panel usa el puerto 8765 y Ollama el 11435. Los demás ordenadores del laboratorio no intervienen. No se reemplaza otra instalación de Blender, Python ni Ollama.

El primer arranque prepara Qwen3-VL, embeddings multilingües y Whisper. Las versiones de los programas descargados se fijan y sus archivos se verifican con SHA-256 antes de extraerlos. Los modelos se descargan desde sus proveedores; no se incluyen en el ZIP.

## Blender for Dental

Sin B4D instalado, SEGMENT IQ utiliza su **motor propio** con Blender 3.6.23 y Tissue. Conserva los pasos, referencias y controles del laboratorio, pero no afirma ejecutar las herramientas propietarias de B4D.

No se distribuyen módulos ni licencias de B4D. El adaptador existente de cemento se desarrolló para la instalación antigua del laboratorio. La distribución actual de B4D utiliza Blender 4.5 y todavía requiere adaptar y validar ese puente antes de activarlo aquí. Comprar o instalar B4D por sí solo no demuestra compatibilidad con este adaptador. [Información del fabricante](https://www.blenderfordental.com/shop).

## Biblioteca y casos

El instalador indexa las skills y procedimientos incluidos en el repositorio. Puedes subir STL, escenas, documentos, vídeos y correcciones desde el panel local. Las mismas reglas de construcción y revisión siguen aplicándose.

El ZIP público no contiene los casos, vídeos ni corpus privado del laboratorio. Esos materiales deben trasladarse por un medio privado y cargarse en la biblioteca del Mac. No copies sin adaptar la base de datos de Windows: contiene rutas absolutas a ese equipo. Tampoco copies `config.local.json`, sesiones de Codex o licencias entre ordenadores.

## Comprobaciones y límites

La automatización [Mac local Apple Silicon](https://github.com/piguin40-eng/segment-iq-public/actions/workflows/macos-local.yml) instala desde cero en macOS arm64 y verifica dependencias, pruebas de la aplicación, un puente sintético a través de las 13 etapas, servicios locales, RAG semántico, Ollama y Whisper. Consulta el resultado de la ejecución asociada a la versión; una ejecución pendiente o fallida no es una validación.

La versión 0.6.0 tiene [validación nativa completada](MAC_VALIDACION_2026_11_19.md), con retenciones, captura del visor y arranque mediante LaunchAgents.

La prueba automatizada no utiliza una cuenta personal de Codex, B4D licenciado ni casos de pacientes. Tampoco valida la interfaz gráfica, el micrófono o permisos de captura en tu Mac físico. Esos permisos se conceden localmente cuando macOS o el navegador los solicitan. Los resultados geométricos siguen pendientes de revisión del laboratorio; la instalación no convierte un caso en aprobado para fabricar.

## Cliente remoto anterior

Los DMG `0.6.0-preview.1` de la publicación anterior son clientes que se conectan a otro servidor. No son este instalador local. Para usar todo en el propio Mac, utiliza el ZIP local de arriba. Puedes conservar el cliente anterior para conectarte a un servidor distinto.

## Referencias de los componentes

- [Blender 3.6 y archivos oficiales](https://download.blender.org/release/Blender3.6/).
- [Instalación oficial de uv](https://docs.astral.sh/uv/getting-started/installation/).
- [Ollama en macOS](https://docs.ollama.com/macos).
- [Codex CLI e inicio de sesión](https://learn.chatgpt.com/docs/codex/cli).
