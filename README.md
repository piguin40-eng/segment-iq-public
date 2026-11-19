# SEGMENT IQ

Código completo del agente de segmentación dental del laboratorio: servidor, interfaz, motor Blender, RAG audiovisual, correcciones, skills, pruebas y cliente de escritorio.

**Servidor y motor: 0.5.25 · Cliente: 0.6.0-preview.1 · Copia pública: 19 de noviembre de 2026.**

## Descargar en tu Mac

- [Proyecto completo en ZIP](https://github.com/piguin40-eng/segment-iq-public/archive/refs/heads/main.zip): descarga y descomprime para conservar todo el código.
- [Descargas de la versión](https://github.com/piguin40-eng/segment-iq-public/releases/tag/v0.5.25-public.1): código, verificaciones y paquetes disponibles.
- [Guía para Mac](docs/MAC.md): diferencia entre descargar el proyecto y usar el cliente de escritorio.

El cliente Mac se conecta al servidor del laboratorio. **El motor de segmentación local está preparado para Windows; su ejecución nativa en Mac sigue pendiente.** Descargar el código no instala Blender, B4D ni los modelos de IA. Los paquetes de escritorio son versiones de evaluación sin firma/notarización del titular.

## Qué contiene

| Carpeta | Contenido |
|---|---|
| `dental_lab/` | Servidor, autenticación, cola, RAG, biblioteca, casos, dictado e interfaz roja SEGMENT IQ |
| `engine/` | Preparación automática del STL, construcción, exportación y controles geométricos |
| `openclaw/` | Instrucciones, skills y procedimiento del laboratorio para otro agente |
| `desktop/` | Cliente Electron para macOS Intel/Apple Silicon y Windows |
| `docs/` | Instalación, API, correcciones, visor y límites comprobados |
| `commercial/` | Preparación comercial y requisitos todavía pendientes; no constituye autorización de venta |
| `tests/`, `.github/workflows/` | Pruebas y automatización de compilación |

Los casos, escenas de pacientes, vídeos, audios, índices del RAG, resultados, credenciales, modelos descargados y componentes propietarios de Blender for Dental **no se publican**. El RAG está incluido como software; su biblioteca privada se guarda y transfiere por separado.

## Instalar el servidor en Windows

Con Python 3.12 y Blender 3.6 disponibles, abre PowerShell en la carpeta del proyecto:

```powershell
./Install-Lab.ps1 -Python 'C:/ruta/python.exe' -EnableNetwork -StartAtLogin
```

La instalación separa código, datos y entornos. Configura B4D con tu propia instalación/licencia y consulta [la guía de instalación](docs/GUIA_INSTALACION_LAB.md), [el acceso](docs/ACCESO.md) y [el arnés Codex](docs/ARNES_CODEX.md). Los modelos se preparan con `Setup-Models.ps1`. La cuenta y los datos del laboratorio original no forman parte de esta descarga.

## Usar e iterar

1. Sube el STL sin segmentar y crea el caso.
2. Sigue la construcción y consulta sus medidas y resultados.
3. Añade correcciones, imágenes o dictado y solicita el rediseño del mismo trabajo.
4. Revisa primaria, secundaria, conexiones, espesores y extracción antes de aprobar.

La skill del laboratorio se incorpora a la planificación y revisión. La recuperación del RAG no entrena los pesos del modelo ni acredita por sí sola que la geometría cumpla. El adaptador B4D documenta la herramienta de cemento; el resto de etapas son del motor propio. El resultado sigue sujeto a revisión del laboratorio.

## Desarrollo

```text
python -m venv .venv
python -m pip install -r requirements-lock.txt -r requirements-geometry.txt
python -m pytest -q tests commercial/test_readiness.py
node --test tests/dictation_ui.test.cjs desktop/test/policy.test.cjs
```

Activa primero el entorno virtual. El cliente usa Node.js 24, pnpm 11.19.0 y su archivo de dependencias fijadas; consulta [desktop/README.md](desktop/README.md).

Esta publicación reúne una copia del motor instalado y el cliente de escritorio, sin alterar el servicio del laboratorio ni publicar su historial privado. Consulta [el alcance de la distribución](DISTRIBUTION.md) y [los cambios del motor](docs/PREPARACION_AUTOMATICA.md).
