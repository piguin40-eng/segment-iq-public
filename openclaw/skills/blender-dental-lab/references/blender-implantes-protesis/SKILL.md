---
name: blender-implantes-protesis
description: Diseñar o corregir coronas y pilares protéticos sobre implantes ya alineados en Blender for Dental, siguiendo la referencia B4D Zoom Implant Crowns y los criterios del laboratorio. Distinguir restauración, pilar y modelo con análogos; preservar conexiones, registro y anatomías. No es una skill de planificación quirúrgica ni de fabricación de implantes intraóseos.
---

# Prótesis sobre implantes

Versión 1.0.0 · `LAB-IMPLANTES-PROTESIS-20260916`.

Leer el [procedimiento temporizado del vídeo](references/video-implant-crowns.md) para elegir la rama apropiada y las [condiciones del laboratorio](references/aplicacion-laboratorio.md) antes de generar o corregir geometría. Consultar ambas referencias al preparar y revisar un diseño sobre implantes en SEGMENT IQ.

## Preparar el caso

Localizar el caso, escaneos, antagonista, anatomías, componentes y última escena del técnico. Si los implantes ya están alineados y verificados, conservar esas transformaciones; no repetir el alineamiento por imitar el vídeo. Recuperar en el RAG las notas del caso y `LAB-IMPLANTES-PROTESIS-20260916`, junto con `LAB-DISENO-DENTAL-20260916` para anatomía y colocación.

Identificar el objetivo antes de operar: corona sobre componente comercial, pilar personalizado o modelo impreso con análogos. Un alojamiento de análogo no es la conexión protética final. Registrar la referencia y procedencia de cada componente. Buscar la información en los archivos y biblioteca disponibles; no inferir compatibilidad comercial por parecido visual ni solicitar un JSON al técnico.

## Construir y corregir

Abrir una copia versionada del caso. Mantener escaneos, anatomías y geometrías de conexión en objetos/colecciones identificables. Aplicar la rama documentada con los módulos B4D realmente disponibles. Comprobar el resultado de cada operación y conservar los parámetros y objetos usados; el texto de la skill no ejecuta el complemento.

Proteger las superficies funcionales de conexión frente a esculpido, remallado y cortes. Revisar la corona y la chimenea como partes distintas de la conexión; una modificación visible del canal no demuestra compatibilidad de tornillo, instrumental o componente. Resolver el canal con la geometría y documentación del sistema del caso.

Traducir cada corrección en un cambio local identificable y comparar con la versión anterior. Conservar la colocación manual aceptada. Revisar arcada, contactos interproximales, transición cervical y oclusión sobre el antagonista registrado. Mantener como pendientes las comprobaciones que no puedan medirse con las entradas existentes.

Cuando se pida diseñar un puente y después segmentarlo, presentar el diseño al laboratorio en el punto de revisión acordado. Tras su validación, aplicar `blender-barras-video` al STL del diseño correspondiente. Una corona individual o un modelo con análogos no necesita automáticamente la segmentación de barra.

## Dejar evidencia utilizable

Conservar escena antes/después, archivos de entrada, transformaciones, componentes, versión de Blender/B4D, operaciones ejecutadas, medidas y vistas comparables. Indicar qué datos vienen del laboratorio, del vídeo o de una propuesta del agente. No entregar una referencia terminada del laboratorio como autoría propia ni declarar resuelta una corrección que no produjo cambio geométrico.

La referencia estudiada es un tutorial externo de 2020 con transcripción automática y contraste visual parcial. Verificar nombres de botones y efectos en la instalación actual antes de reproducirlos. Los errores y dudas del tutorial son límites de evidencia, no reglas de diseño. Indexar esta skill no entrena pesos ni incorpora automáticamente un motor de coronas/pilares a la aplicación.
