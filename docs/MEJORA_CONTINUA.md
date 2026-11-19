# Cómo acercar las segmentaciones al criterio del laboratorio

El sistema conserva evidencia y la usa en nuevas consultas. No modifica automáticamente los pesos del modelo ni convierte cualquier vídeo en instrucciones aprobadas.

## Registro de cada caso

Conservar STL bruto, perfil utilizado, código/commit, ejecuciones, métricas, vistas y decisión del técnico. Una corrección útil indica zona, defecto y resultado esperado: por ejemplo, falta altura de barra en una región, soporte distal incompleto o retención demasiado profunda. Las medidas deben indicar su caso y marco de coordenadas.

La aprobación se asocia a la última generación terminada del caso; si hay una nueva generación pendiente o fallida no se debe aprobar la anterior por accidente. Las revisiones anteriores permanecen disponibles. Antes de promover una modificación del motor, comparar la misma entrada con el código anterior y con el nuevo.

## Material audiovisual

Guardar vídeos del proceso completo, preferentemente con narración de las decisiones, unidad de medida y resultado final. El índice extrae audio, textos de interfaz y descripciones de capturas, conservando el momento de origen. El muestreo no reemplaza la inspección del vídeo si hay que deducir selecciones, acciones rápidas o propiedades que no se leen.

Marcar en las correcciones qué observaciones de un tutorial adoptáis en el laboratorio. Mantener separados criterios generales, parámetros de un caso, pruebas rechazadas y propuestas pendientes. Recuperar varias fuentes cuando haya contradicciones; no asumir que el documento más largo o reciente manda sobre una aprobación concreta.

## Evaluación del motor

Mantener un conjunto privado de casos aprobados que represente superior/inferior, distintos ejes y radios, extremos sin implante y variaciones de altura. Empezar con el caso inferior documentado; no declarar cobertura de un tipo de caso hasta construirlo y revisarlo.

En cada cambio: comprobar mallas cerradas, componentes, canales, asientos, solapamiento y coordenadas; revisar secciones locales de altura/profundidad, cobertura distal y retenciones. Los controles actuales no calculan espesor mínimo global, inserción ni ajuste clínico. Registrar las carencias y añadir mediciones relevantes antes de llamar a un cambio una mejora.

El RAG y los expedientes guardan el material necesario para este ciclo. Desde 0.5 el arnés Codex puede interpretar, adaptar parámetros/código numérico de forma, ejecutar y revisar el caso con hasta tres intentos. La promoción automática al motor común, el entrenamiento de pesos y una evaluación geométrica universal no están implementados. El laboratorio decide si el diseño corresponde a su criterio. Ver [ARNES_CODEX.md](ARNES_CODEX.md).
