# SEGMENT IQ — agente local de segmentación y aprendizaje

Versión 0.5.25 para un laboratorio con Blender 3.6 en Windows. Incluye panel de red, RAG local, entrada de vídeos/documentos, memoria de correcciones, expedientes de casos y un ciclo Codex → Blender → comprobación → revisión. Ver [arnés del agente y alcance](ARNES_CODEX.md).

## Qué funciona

- Dictado en español para correcciones y consultas: micrófono, notas de audio, transcripción local editable y reintento sin volver a grabar. El micrófono requiere localhost o HTTPS; no funciona desde el acceso HTTP de otro ordenador. [Uso del dictado](DICTADO.md).

- Visor de construcción con ventana real de Blender capturada tras operaciones, vistas por etapas, reproducción, pausa, seguimiento y pantalla completa; errores e indicaciones pendientes en la misma pantalla. La captura de ventana requiere habilitar `live_blender` en la configuración local. [Uso y alcance](VISOR_Y_B4D.md).
- Integración local con la herramienta de cemento de Blender for Dental iBar, con comprobación del resultado y recibo de ejecución; el resto del motor sigue siendo propio.
- Altura anterior diferenciada, con comprobación posterior en secciones. La reserva oclusal de supra se aplica y mide; el espesor mínimo global en paredes y márgenes sigue pendiente.

- Biblioteca con deduplicación por SHA256 e indexación incremental de una carpeta de entrada.
- Vídeos: transcripción local en español (faster-whisper), fotogramas muestreados, OCR (RapidOCR), descripción visual con modelo local y referencias al segundo. Puede abrirse el vídeo en el instante citado.
- RAG híbrido: SQLite FTS5 y embeddings multilingües locales de 384 dimensiones. Respuesta generada por Qwen3-VL 4B mediante Ollama, con fuentes separadas de instrucciones.
- Correcciones con técnico, caso, fecha, estado y hasta 20 adjuntos. “Aplicar correcciones y rediseñar este trabajo” encola una segmentación con una copia del historial existente en ese momento.
- Casos: registro de STL, medidas globales, plan del agente con fuentes, perfil específico, cola de ejecución Blender, resultados y revisión.
- Acceso con usuario y contraseña del laboratorio, guardada como hash con sal; clave API independiente. Servidor de aplicación en puerto 8765. Ollama escucha solo en loopback.

## Alcance real

El motor genera primaria, supra y retenciones desde el STL bruto. La versión 0.3.2 localiza chimeneas por sus ejes y paredes, admite puentes cortos con menos de tres conexiones y protege el perímetro funcional medido, tanto sobre interfases como en geometrías de conexión directa. No solicita un JSON ni una marca de implante al técnico. Conserva el orden de 13 etapas del patrón reconstruido del laboratorio, con seguridad geométrica adaptada. Se han generado propuestas revisables SUP, INF y de un puente de tres piezas; esto no prueba funcionamiento universal ni aprobación clínica. Si falla el detector o los controles, conserva diagnóstico y etapas.

Las indicaciones simples de más/menos altura, profundidad o anchura y la altura anterior diferenciada generan ajustes de parámetros. Las ambiguas, las regiones todavía no reconocidas y los adjuntos se conservan como pendientes de interpretar. El informe y el visor distinguen ajustes aplicados de pendientes, desglosando notas mixtas. No interpreta automáticamente cualquier corrección de una captura.

El RAG conserva y recupera conocimiento, no reentrena los pesos del modelo. El aprendizaje progresivo consiste en registrar correcciones, recuperar ejemplos aceptados, proponer cambios y comprobarlos con casos de referencia. No se activa autoentrenamiento ni modificación automática de código tras cada vídeo.

El asistente valida formato, referencias existentes y una comprobación limitada de unidades. Si el modelo no supera esos controles tras un reintento, muestra las fuentes sin presentar un resumen como validado. Durante la prueba se detectaron respuestas repetitivas y confusión volumen/altura; esos controles reducen el fallo, pero no verifican automáticamente toda afirmación técnica. El modelo local de 4B es un asistente inicial, sujeto al criterio del técnico.

El muestreo visual predeterminado es cada 20 segundos con exclusión de imágenes casi iguales y límite de 720 capturas. Se registra la cobertura parcial cuando se alcanza el límite. No reconoce todos los clics y movimientos entre fotogramas. Una descripción de imagen es una inferencia sin revisar, no evidencia de dimensiones ilegibles.

## Instalación en el laboratorio

En PowerShell, con Python 3.12 disponible:

```powershell
./Install-Lab.ps1 -Python 'C:/ruta/python.exe' -EnableNetwork -StartAtLogin
```

El destino predeterminado es `%USERPROFILE%/Documents/DentalLabAgent`. Separa `app` (código), `data` (casos, conocimiento y clave), y `runtime` (Python/modelos). No requiere que OpenClaw esté instalado. La integración opcional está en `openclaw/`; ver `docs/OPENCLAW.md`.

El instalador prepara Python y Blender. Ollama portable y sus modelos se preparan con `Setup-Models.ps1`; la instalación entregada en CAD-CAM se verifica aparte en el informe local. Los modelos externos conservan sus licencias y no se incluyen en Git.

El inicio automático se realiza al iniciar sesión del usuario Windows. No es un servicio que funcione antes del inicio de sesión. La regla de firewall limita el acceso al puerto 8765 desde la subred local y perfiles Privado/Dominio; crear esa regla puede requerir administrador. No abrir el puerto a Internet.

En el equipo: `http://localhost:8765`. En la red: `http://NOMBRE-EQUIPO:8765`. Las indicaciones de acceso y rutas están en `ACCESO_LAB.txt`, fuera del repositorio. Ver [configuración del usuario](ACCESO.md). El servicio usa HTTP para la LAN; si se conecta desde fuera, añadir un acceso privado o proxy TLS, no publicar directamente el puerto.

## Uso diario

Abre **SEGMENT IQ** desde su icono rojo en el escritorio. El acceso comprueba el servicio, lo inicia si está apagado y abre el panel en el navegador. `Create-DesktopShortcut.ps1` permite volver a crear el icono sin reinstalar. El instalador también lo crea, salvo que se indique `-NoDesktopShortcut`.

1. Arrastrar vídeos/documentos a Biblioteca, elegir varios archivos con el selector o copiarlos a `data/inbox` (puede compartirse esa carpeta con permisos del laboratorio).
2. Revisar que la indexación termine y consultar con citas. Reindexar materiales con errores o cuando se habilite un modelo pendiente.
3. Arrastrar el STL bruto a Casos. Pulsar **Crear y segmentar**: se mide y encola Blender automáticamente.
4. Seguir los pasos en la tarjeta y abrir **Ver resultados** para inspeccionar vista, STL y escenas. La propuesta requiere revisión.
5. Pulsar **Corregir / Iterar** y **Aplicar correcciones y rediseñar este trabajo**. Se reconstruye desde el original con las observaciones existentes al solicitar la versión. Ejemplo: «más altura 0,5 mm». El informe señala ajustes aplicados y pendientes. Las versiones anteriores se conservan.

La cola se conserva en SQLite. Una ejecución interrumpida al reiniciar se marca como interrumpida y no se presenta como terminada. Reintentar desde una carpeta nueva conserva el diagnóstico anterior.

## Desarrollo y pruebas

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pytest -q
```

`requirements-lock.txt` fija las dependencias del agente y `requirements-geometry.txt` las del motor en su entorno independiente. La API no recibe comandos de shell. Con el arnés Codex activo, el agente puede editar parámetros y adaptadores numéricos en una copia del caso; el supervisor comprueba su alcance y conserva los verificadores del motor instalado.

## GitHub y copia de seguridad

Esta copia publica solo software y documentación; conserva el directorio de datos en un almacenamiento privado. `.gitignore` excluye casos, vídeos, índices, claves, modelos y resultados. Los historiales originales y escenas del laboratorio pertenecen a `data`, no al repositorio. Antes de publicar, ejecutar `scripts/check_repository.py` sobre los archivos preparados para commit.

La orden `python -m dental_lab.cli backup` crea una copia coherente de SQLite y copia los originales, derivados, perfiles y resultados en `DentalLabAgent/backups/FECHA`. La configuración con la clave y los modelos se conservan aparte; no se envían a GitHub.

Fuentes técnicas: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [RapidOCR](https://github.com/RapidAI/RapidOCR), [FastEmbed](https://github.com/qdrant/fastembed), [Qwen3-VL en Ollama](https://ollama.com/library/qwen3-vl:4b-instruct). Las pruebas de esta instalación se documentan en el informe de entrega, sin incluir casos privados en el código.

## Novedades 0.3.0

Creación y cola de geometría atómicas, preparación interna, prevención de duplicados, avance por etapas y prioridad de segmentación frente a indexaciones todavía en cola. Los trabajos ya iniciados terminan primero. Recuperación de referencias sin bloquear por el modelo de lenguaje. Booleanas de doble precisión e intercambio STL ASCII. Ver [algoritmo y límites](PREPARACION_AUTOMATICA.md).

## Novedades 0.2.1

Inicio de sesión con usuario y contraseña, hash PBKDF2-SHA256 y límite de intentos. La cuenta se configura localmente mediante `set-login`; las credenciales API existentes se conservan y no se publican.

## Novedades 0.2.0

Marca SEGMENT IQ, paleta roja/coral, carga por arrastre y selector con progreso por archivo, reintentos que reutilizan las subidas completadas, creación directa desde STL y revisiones con adjuntos. La instalación conserva el directorio DentalLabAgent y el módulo dental_lab para mantener los datos existentes. Ver [Guía de uso](GUIA_SEGMENT_IQ.md).
