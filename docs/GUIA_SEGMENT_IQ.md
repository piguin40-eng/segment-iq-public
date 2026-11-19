# SEGMENT IQ · Guía del laboratorio

## Añadir material de aprendizaje

En Biblioteca, arrastra varios vídeos, capturas o documentos sobre la zona roja, o pulsa para elegirlos. Verás los nombres antes de enviarlos y puedes quitar cualquiera. Pulsa **Incorporar a la biblioteca**: cada archivo muestra su progreso. Si falla una subida, vuelve a pulsar; los archivos guardados se reutilizan. Después consulta el estado de indexación en la lista inferior.

También puedes copiar material a la carpeta de entrada indicada en la aplicación. Las descripciones de imágenes y transcripciones son observaciones pendientes de revisión del laboratorio.

## Empezar un diseño

En Casos, arrastra el **STL sin segmentar**, escribe el nombre del caso y pulsa **Crear y segmentar**. También puedes elegir un STL ya guardado. El agente mide el STL y ejecuta Blender automáticamente. Verás el paso actual en la tarjeta y podrás abrir **Ver resultados**. No hace falta subir un JSON.

## Corregir e iterar

1. Abre **Corregir / Iterar** en la tarjeta del caso. El formulario queda asociado a ese caso y muestra sus revisiones anteriores.
2. Escribe el nombre del técnico, la zona que necesita cambios y el resultado que buscáis. Si aportas medidas, indica a qué región del caso corresponden.
3. Arrastra capturas, vídeos o archivos de referencia; son opcionales, hasta 20 por revisión.
4. Pulsa **Guardar corrección**, o **Aplicar correcciones y rediseñar este trabajo** para ejecutar Blender con las indicaciones.
5. En el historial, abre **Ver revisión** para abrir los resultados, las medidas, las fuentes y el historial utilizado. Las revisiones anteriores permanecen disponibles.

El análisis usa las 8 observaciones más recientes del caso y las 2 generales más recientes, más un fragmento de hasta 4 adjuntos, con un máximo de 1100 caracteres por fuente. El archivo del historial conserva las observaciones completas y documenta estos límites. Si un adjunto no se ha podido interpretar, queda identificado como pendiente de inspección.

La nueva versión reconstruye desde el original. Admite cambios simples de más/menos altura, profundidad y anchura. «Más altura 0,5 mm» propone ese incremento; sin cifra, usa 0,5 mm. Las indicaciones sobre una pieza/zona o una captura se conservan como pendientes de interpretar. Comprueba el informe antes de dar una indicación por aplicada.

Aprobar requiere una generación real terminada. Si un intento falla, **Ver resultados** conserva el diagnóstico; no hace falta subir un perfil ni una segmentación terminada.

## Dónde queda guardado

Los casos, vídeos, capturas y correcciones permanecen en los datos privados de este ordenador. El código y las instrucciones para OpenClaw están en el paquete de SEGMENT IQ. El nombre interno de la carpeta DentalLabAgent se conserva para mantener la instalación y su biblioteca.

## Rediseñar con correcciones ya guardadas (0.3.1)

En **Criterio del laboratorio**, el bloque rojo **Rediseñar el mismo trabajo** permanece visible. Elige el trabajo y pulsa **Aplicar correcciones y rediseñar este trabajo**. Si la corrección ya está guardada, deja el cuadro de texto vacío: se usan las observaciones del caso y los criterios generales sin duplicarlas ni volver a pedir archivos. Si has escrito una nueva, se registra en el trabajo seleccionado y se encola el rediseño en la misma operación.

El botón no permite cambiar de caso una observación específica escrita para otro trabajo. Una observación general nueva se registra en el trabajo elegido al rediseñar; para promoverla a criterio general, guardarla como general antes de pulsar el botón. Aprobar no es una orden de rediseño.

Debajo aparecen las versiones del mismo trabajo, las dos propuestas completadas más recientes, enlaces a archivos y los ajustes aplicados o pendientes. Rediseñar ejecuta el motor disponible: no convierte una corrección regional no interpretada en una corrección aplicada ni garantiza que la nueva forma sea mejor. La revisión del laboratorio sigue determinando eso.
