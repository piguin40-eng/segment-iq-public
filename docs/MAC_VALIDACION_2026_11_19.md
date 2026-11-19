# Validación de la instalación local Mac · 19 de noviembre de 2026

Código comprobado: `0e5e45ed9a2a639f4002641fc314a90e2b725252`. La publicación añade documentación; el instalador y código ejecutable son los mismos que en estas pruebas.

- [Ejecución completa en macOS 15 arm64: aprobada](https://github.com/piguin40-eng/segment-iq-public/actions/runs/44548624161).
- [Regresión Windows: aprobada](https://github.com/piguin40-eng/segment-iq-public/actions/runs/44548624667).
- [Informes, escenas sintéticas y capturas de la ejecución Mac](https://github.com/piguin40-eng/segment-iq-public/actions/runs/44548624161/artifacts/14543226539). GitHub puede exigir sesión para estos artefactos y aplica su plazo de conservación; el ZIP de instalación de Releases se descarga públicamente.

## Resultado observado

| Comprobación | Resultado |
|---|---|
| Instalación desde cero en ruta con espacios | Correcta, sin Windows ni credenciales del laboratorio |
| Blender 3.6.23 arm64 | Importación STL y Tissue disponibles |
| Codex CLI 0.170.0 | Ejecutable y opciones del arnés disponibles |
| Aplicación y geometría | 267 pruebas Python aprobadas en Mac; 266 y una exclusión POSIX en Windows |
| Interfaz y política del cliente | Pruebas Node aprobadas, incluidos siete escenarios de dictado |
| Construcción sintética | Las 13 etapas finalizadas, con retenciones duales obligatorias |
| Primaria y secundaria sintéticas | Controles geométricos PASS; revisión de diseño PENDING |
| Visor de Blender | 20 capturas de operaciones reales de su propia ventana; última captura inspeccionada |
| Arranque del usuario | Los dos LaunchAgents se cargaron y los servicios respondieron |
| Acceso al panel | API local disponible y autenticación comprobada |
| Biblioteca | Skills indexadas, embeddings y consulta semántica correctos |
| Modelo local | Qwen3-VL respondió a una petición de inferencia por Ollama |
| Voz | Whisper cargado y probado con una entrada sintética de audio |

La retención de la prueba partió de 10.118 caras de superficie, se redujo a 151 y produjo una malla dual de 308 vértices y 461 aristas. Son datos del ensayo sintético, no parámetros clínicos recomendados.

El archivo de evidencias descargado coincide con el SHA-256 publicado por GitHub: `fdd3800df1f05859ae1ed367b061f502709d36a0c27c50231b8cc0fd9b3c5c45`.

## Alcance

El ensayo utilizó un puente geométrico sintético de dos conexiones, sin datos de pacientes. No acredita el diseño de un caso real, todos los espesores, inserción ni resistencia. Mantiene la revisión del laboratorio pendiente.

No se usó una sesión personal de Codex ni B4D licenciado. El agente requiere iniciar sesión con la cuenta del usuario en el Mac. B4D no está incluido y el adaptador para la versión actual sigue pendiente de adaptación y validación. Tampoco se han probado el Mac físico del usuario, su micrófono ni sus permisos particulares. El ensayo de Ollama acredita inferencia local, no la exactitud del análisis de todos los vídeos.

Se conservó intacta la instalación Windows del laboratorio. La publicación contiene software, instrucciones y pruebas; el corpus privado y los expedientes no se publican.
