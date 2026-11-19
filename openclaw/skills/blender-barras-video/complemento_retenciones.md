# Retenciones solicitadas por el laboratorio

Procedencia: procedimiento previamente contrastado de `blender-dental-patron`, etapa 9, derivado de las escenas SUP/INF y del historial de operadores entregado por el laboratorio. Es un complemento separado: el vídeo Blender Barras no demuestra esta secuencia dual-mesh ni exige retenciones en todos los casos.

Cuando una corrección vigente del caso exige retenciones, usar `dual_required`. La petición explícita de el laboratorio del 17/09/2026 para el caso 00110 exige que se incorporen; no se cumple entregando una primaria lisa ni citando el carácter opcional de otro ejemplo.

1. Construir una primaria continua con soporte suficiente, conexiones conservadas y reserva de secundaria antes de añadir surcos.
2. Extraer su propia superficie de contacto (`surfaces`), excluyendo márgenes, conexiones y paredes insuficientes.
3. Decimar la superficie y generar `dual_mesh`. Quitar las caras conservando la red de aristas.
4. Proyectar la red sobre la primaria propia, subdividir y volver a proyectar. Dar sección mediante Skin, suavizar mediante Subsurf, remallar y suavizar la herramienta.
5. Recortar con la protección funcional completa y restar la herramienta de la primaria. No alterar conexiones para conseguir un surco.
6. Guardar superficie, red, herramienta y primaria antes/después. Comprobar sustracción efectiva, continuidad, ausencia de perforaciones y disposición de la red en varias vistas.

Los radios y offsets deben distinguir valores recuperados de propuestas. El motor actual documenta Skin de 0,325 mm como propuesta de una revisión, NO como valor confirmado del historial del laboratorio. La proyección de 0,1 mm se atribuye al script B4D instalado. No presentar estos números como universales ni atribuirlos al vídeo. Mantener su procedencia visible en la revisión.

Una red vacía o descartada por el control no satisface `dual_required`: localizar la causa en la superficie o el cuerpo de barra y reconstruir. El control de componentes, protecciones y espesor se conserva. Una limitación real queda identificada como pendiente, nunca como retención realizada.
