# Dictado de correcciones e indicaciones · 0.4.3

En **Criterio del laboratorio**, selecciona el caso y pulsa **Dictar corrección**. En **Consultar al agente** está **Dictar indicación**. Permite el micrófono cuando lo solicite el navegador, habla y pulsa **Detener y transcribir**. El contador y el estado indican cuándo está grabando. Cada nota admite dos minutos. Se puede cancelar mientras se espera permiso, durante la grabación o durante la transcripción.

La transcripción se añade al texto que haya en ese momento, sin sustituir el borrador. Revisa especialmente piezas, decimales y unidades. Después utiliza **Guardar corrección**, **Aplicar correcciones y rediseñar este trabajo** o **Consultar**, según corresponda. El dictado no envía indicaciones ni genera geometría por sí solo. Mientras está activo no se puede guardar, rediseñar o cambiar el caso seleccionado. Cambiar de sección o cerrar la sesión cancela el dictado pendiente y apaga el micrófono; un resultado tardío no se inserta en el borrador.

**Transcribir audio** acepta WAV, WebM, OGG/Opus, M4A/MP4, MP3 y FLAC de hasta 20 MB y dos minutos. Permite utilizar notas grabadas aunque el micrófono del navegador no esté disponible. Si falla el servidor se conserva la nota en la página para **Reintentar transcripción**. El reproductor permite escucharla. Un texto que no cabe en el campo se muestra completo aparte, sin truncar ni borrar el borrador.

## Acceso al micrófono

En el ordenador que ejecuta SEGMENT IQ, utiliza `http://localhost:8765` o `http://127.0.0.1:8765` y un navegador con MediaRecorder. En otros ordenadores, el micrófono necesita un acceso HTTPS con certificado confiable. El acceso de red actual por `http://NOMBRE-EQUIPO:8765` permite usar la aplicación y transcribir archivos, pero el navegador bloquea la captura del micrófono. Esta actualización no instala certificados ni cambia las protecciones del navegador. Las restricciones de un navegador integrado también pueden impedir el permiso; en ese caso abre la aplicación en Chrome o Edge. [Requisitos de getUserMedia, MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

## Procesamiento local y privacidad

`POST /api/dictation?format=webm` recibe audio binario con la autenticación y comprobación de origen habituales. El límite de bytes se aplica mientras se lee el cuerpo, también sin Content-Length. Se fuerza el contenedor de audio indicado y se limita el audio decodificado a 120 segundos de muestras a 16 kHz mono. Se rechazan formatos incorrectos, audio vacío, silencio y duraciones superiores al límite.

El motor faster-whisper instalado transcribe en español en CPU con dos hilos, detección de voz y un vocabulario dental orientativo. El audio no se envía a un servicio de reconocimiento externo. La primera carga reutiliza o descarga el modelo `small` en la carpeta local de modelos. Hay una transcripción de dictado simultánea; si otra está en curso se devuelve un mensaje para reintentar. El audio temporal se elimina al terminar o fallar; no se registra como fuente, corrección ni trabajo. Solo el texto revisado que el técnico guarde entra en el historial normal y el RAG. [Motor faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Verificación

Pruebas de autenticación, origen, tamaño de cuerpo, duración decodificada, silencio, errores, limpieza del audio y ausencia de escrituras de correcciones o fuentes. Pruebas de interfaz con micrófono simulado: cancelación del permiso, liberación de pistas, borradores editados durante la transcripción, respuestas tardías, límite del campo, HTTP y reintento. Ensayo del transcriptor instalado con voz sintética española de prueba: reconoció «0,5 milímetros», «interfase», «chimenea» y «pieza 37». El permiso y el micrófono físico de cada equipo los controla su navegador.
