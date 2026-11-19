# Correcciones geométricas · 0.4.5

## Terminación, crestas y afinado

La versión 0.4.5 reconoce por separado «terminación continua sin picos», «reducir la pirámide superior», «bisel/visel de apoyo» y «barra más fina», también con la errata «labarra». Una nota guardada a la vez en criterio general y caso por el mismo técnico se aplica una sola vez. Una observación posterior independiente puede volver a afinar la barra.

Sin cotas expresas, propone un bisel cervical de 0,20 mm en los perfiles de construcción y un afinado de 0,20 mm por lado por observación, hasta 0,80 mm acumulados y siempre limitado por los hombros funcionales. Son parámetros de propuesta para revisar, no medidas universales aprobadas. Las cotas expresas de estas nuevas operaciones todavía requieren adaptación y quedan pendientes; no se sustituyen silenciosamente por el valor propuesto.

El contorno se suaviza sobre el trazado propio sin mover los ejes. El techo se mide únicamente en su superficie interior superior: incluir bordes cervicales bajos produce una rebaja excesiva. Se redondea mediante una envolvente que no eleva valles y se eliminan las crestas longitudinales entre conexiones. El separador de supra se ajusta con espacio de cemento y después se reincorporan las regiones funcionales. Se registran reducción de cresta y volumen retirado en `roof_refinement`, dentro de `Seguridad_oclusal_local.json`.

Las líneas pintadas en capturas orientan la interpretación del técnico/agente; no se presentan como una curva 3D extraída píxel por píxel. Comparar la terminación y el bisel en las vistas finales, después del remallado, y comprobar también retenciones, exportación y conexiones. El mínimo de paredes y márgenes continúa pendiente.

Cuando no hay cambios interpretados, el intento queda como «Sin cambios nuevos» y la propuesta anterior sigue pendiente de revisión; no se marca como un error de Blender ni se fabrica otra copia. Las correcciones no reconocidas permanecen visibles.

## Altura, centrado y conservación

Las notas se interpretan por indicación: «más soporte a la supra» no anula «bajar la barra». Repetir la misma petición dentro de una nota no duplica la rebaja. Una cantidad en milímetros se asocia a su ajuste, sin tomar el espesor mínimo de otra frase como un desplazamiento. Los cambios no interpretados permanecen visibles.

Sin cantidad explícita, una petición de altura propone 0,5 mm por observación; se mantienen los límites de adaptación existentes. No es una medida universal aprobada por el laboratorio. El TOP propuesto y las alturas reales después de la seguridad local son medidas diferentes.

Los puentes lineales miden el eje de cada conexión y centran el trazado entre ambos bordes, conservando el eje original. Las arcadas completas aplican este centrado cuando se solicita expresamente; si no existe soporte bilateral con la reserva oclusal, el intento se detiene y conserva el diagnóstico. La adaptación automática de ese caso sigue pendiente, sin pedir al técnico un JSON ni presentar un trazado descentrado como corregido.

La protección funcional sigue la envolvente medida de la chimenea, manteniendo el perímetro basal y las paredes verificadas. Los rayos toman la primera pared desde el eje; los triángulos detectados se vinculan a sus vértices originales dentro de la zona funcional. La comprobación no se limita a los anillos basales: contrasta el volumen protegido y esas superficies después de exportar. El contorno se une en dos dimensiones y se revoluciona antes de orientarlo para evitar caras internas coincidentes.

Cuando el separador abre ventanas adicionales en la supra, se identifican las regiones aisladas donde alcanza el exterior. La seguridad local rebaja el separador a su alrededor para reservar material y equilibra la rebaja a ambos lados del trazado. Después se reincorporan las protecciones funcionales. Se comprueban componentes, topología, solapamiento, superficies funcionales y espesores oclusales muestreados. Las nuevas perforaciones en primaria o supra bloquean la entrega.

El centrado final se mide en dos secciones de los hombros reales de barra después de las rebajas locales. Ambas deben extenderse más allá del perímetro funcional; comprobar solo un collar circular no demuestra que la barra esté centrada. Se conservan las cotas Z medidas, la distancia a cada borde y el desfase del centro. El umbral de 0,35 mm es un control de este prototipo y requiere revisión de diseño; no certifica ajuste ni resistencia.

La red dual sigue el procedimiento de proyección, Skin y remallado. Antes de restarla, se comprueba cada grupo conectado de surcos sobre la barra resultante. Se excluyen los que generan otra perforación o separan metal, conservando los que superan ese control. `Retenciones_medidas.json` registra ambos grupos y sus zonas. Si no queda ninguna retención segura, la generación se detiene; la exclusión de zonas requiere revisión del laboratorio.

Cada revisión compara sus parámetros, código y volúmenes con la versión anterior. Si los parámetros y el motor geométrico coinciden, no vuelve a ejecutar Blender ni presenta una copia como una mejora. El visor explica la falta de cambio y mantiene accesibles los resultados anteriores.

La limpieza de exportación conserva los índices de vértice del resultado booleano antes de que la fusión por coordenadas del STL pierda esa topología. Se separan únicamente los contactos que esa fusión uniría, con un desplazamiento máximo de 0,000001 mm. Se comprueba el STL recargado tanto en coordenadas de trabajo como originales, y se limita cualquier simplificación alternativa a 0,000001 mm. No se eliminan indiscriminadamente triángulos estrechos de una malla cerrada. Se excluyen únicamente componentes de volumen numéricamente nulo; cualquier segundo componente material bloquea la entrega. Las tolerancias de conservación de conexiones siguen siendo las mismas y se verifican después de exportar. `Limpieza_exportacion.json` registra la operación.

Estas mediciones no acreditan el espesor mínimo global de paredes y márgenes, la trayectoria de inserción ni la aptitud de fabricación. Las correcciones y resultados siguen pendientes de aprobación del laboratorio. El cemento se ejecuta mediante la herramienta local de Blender for Dental; el resto del motor no se presenta como un replay literal de B4D.

Pruebas reproducibles: `tests/test_bar_corrections.py`, `tests/test_chimneys.py`, `tests/test_regional_height.py` y la suite de servicio. Usan figuras analíticas y datos temporales, sin casos del laboratorio en el repositorio.
