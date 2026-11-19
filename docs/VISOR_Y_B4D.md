# Construcción visible y correcciones · 0.4.2

## Ventana real de Blender

En **Casos y segmentaciones → Ver construcción → Ventana de Blender**, las nuevas ejecuciones del laboratorio muestran capturas de la instancia de Blender que está construyendo el caso. Se obtienen después de operaciones reales: entrada, conos individuales, trazado, seis perfiles, remallado, cemento B4D y operaciones de retenciones. **Seguir en directo** muestra la última captura disponible, consultada cada dos segundos; **Reproducir** permite revisar todas las capturas a ritmo de lectura. **Pantalla completa** amplía el visor. Al abrir una versión con capturas se elige esta vista automáticamente.

Es una secuencia de capturas de ventana, no un vídeo continuo ni una simulación de movimientos del ratón. Las operaciones rápidas pueden terminar entre dos consultas y se revisan después con Reproducir. Durante cálculos largos se mantiene la última imagen y la etapa activa sigue indicada. Orientación, booleanas y validaciones calculadas fuera de Blender tienen resultados en **Vistas por etapas**. Las versiones antiguas conservan sus imágenes anteriores, sin fabricar una grabación retrospectiva.

La opción privada `live_blender: true` habilita esta función en el servidor del laboratorio. El ejecutor independiente utiliza `--live-blender`. Requiere una sesión gráfica de Windows iniciada y Blender 3.6. El valor predeterminado es falso para instalaciones sin sesión gráfica. Los pasos Blender 3, 5, 7, 8 y 12 utilizan una ventana dedicada; el resto del motor conserva sus cálculos. No se controla una ventana abierta por el técnico ni se captura su escritorio. Se usa `bpy.ops.screen.screenshot`, con capturas y manifiesto atómicos en `outputs/Proceso/Blender/`; los archivos y el registro requieren el acceso autenticado del caso. Un error de captura queda indicado sin aprobar ni invalidar por sí solo la geometría. El adaptador verifica además la finalización de cada script gráfico: cerrar Blender antes de terminar no puede marcar el paso como correcto.

La sesión se prepara antes de entrar en el contexto gráfico, para evitar que cargar una escena invalide ese contexto. Los puntos de captura ajustan solo la vista y registran operaciones ya realizadas; no añaden mallas, movimientos ni resultados de referencia. Prueba completa desde STL bruto de un puente de dos conexiones: 13 etapas terminadas, 22 capturas de ventana, ocho vistas geométricas y controles finales superados. La herramienta B4D de cemento conserva su recibo de ejecución.

## Vistas por etapas

En **Casos y segmentaciones**, cada trabajo tiene **Ver construcción**. Al crear un caso o rediseñarlo, el visor se abre automáticamente. Muestra vistas reales obtenidas al completar orientación, chimeneas, diseño básico, cemento, separación, retenciones y escena final. No inventa geometría intermedia ni reproduce movimientos de ratón.

**Seguir en directo** muestra la última etapa terminada; **Reproducir**, **Pausar** y el deslizador permiten revisar la secuencia guardada. La etapa activa y el error se muestran separados de la última imagen disponible. Cerrar el visor no cancela el trabajo. Las versiones anteriores a 0.4 no tienen grabación por etapas: se indica expresamente y conservan sus archivos originales.

Las correcciones utilizadas y pendientes aparecen en el propio visor, también mientras se construye. **Corregir este trabajo** lleva al mismo caso; después se usa el botón de rediseño existente. Las observaciones posteriores a la solicitud pertenecen a la próxima versión. Las imágenes se guardan en `outputs/Proceso/`, y `/api/jobs/{id}/progress` sirve el registro autenticado. El registro se reemplaza de forma atómica y solo incluye imágenes cuyo render ha terminado.

## Blender for Dental instalado

La integración requiere Blender 3.6, el módulo iBar y sus menús licenciados cargados en las preferencias del usuario de Windows. El parámetro privado `b4d_root` señala la instalación local. En este laboratorio se recuperó el complemento ausente `pie_menu_editor` desde el instalador ya existente en `ModelDesigner3/b4d1.16.54.zip`; no se redistribuye ese complemento.

El paso 5 ejecuta la herramienta instalada **iBar → Ajustar espacio de cemento**, con una instancia de Blender con contexto de interfaz. El adaptador prepara el CUTTER propio, ejecuta el script local íntegro mediante `pie_menu_editor.ui_utils.execute_script`, comprueba que se haya creado `CuttingTool` con Solidify, ajusta el gap medido del caso y conserva `06_Cemento_B4D.blend` y `B4D_ejecucion.json`. El recibo identifica versión, hash del script, parámetros y alcance. Si falta el complemento o no produce el resultado esperado, la generación se detiene con su diagnóstico: no cambia silenciosamente al motor propio.

Solo esta herramienta está integrada actualmente con el código original de B4D. Trazado, separación, protecciones y retenciones siguen siendo etapas de SEGMENT IQ basadas en el patrón documentado. No se afirma un replay completo de todas las macros del laboratorio. El repositorio contiene el adaptador propio, nunca scripts propietarios, menús cifrados ni licencias de B4D.

## Altura y espesor

Las notas mixtas ya no se tratan como una única instrucción indivisible. La indicación de más altura anterior se mide en la arcada orientada y produce un TOP con transición suave, junto con conos adaptados. La propuesta actual compensa la diferencia cervical medida y añade 1 mm de altura anterior respecto a posterior, limitada por el corredor anatómico. Un puente identificado únicamente como posterior no recibe un aumento anterior inventado. Las indicaciones sobre piezas o regiones todavía no reconocidas siguen pendientes.

Se reserva espacio oclusal y, después de separar, se miden tres líneas internas del trazado. Los controles exigen que la mediana anterior supere a la posterior y que las secciones oclusales medidas alcancen el objetivo de supra solicitado. Una malla cerrada no basta para superar esos controles.

**El espesor mínimo global de 0,8 mm sigue sin quedar acreditado en paredes laterales y márgenes.** La interfaz y el informe conservan esa parte como pendiente; el muestreo vertical no se presenta como sustituto. Tampoco se valida todavía toda la trayectoria de inserción.

Desde 0.4.1, una sección oclusal demasiado fina activa una corrección local del separador. Se comprueban intervalos continuos de material, sin confundir un hueco intermedio de la chimenea con espesor útil. Una superficie de seguridad rebaja solo la zona necesaria; se conserva el gap mediante separación adicional en la herramienta interior y se vuelven a incorporar las protecciones funcionales después de este ajuste. Se guardan medidas antes/después en `Seguridad_oclusal_local.json`. El proceso detiene los ajustes si no mejora el mínimo y permite como máximo tres correcciones medidas; no rebaja el umbral ni elimina el diagnóstico. Esta herramienta propia no se presenta como la macro de seguridad B4D.

## Verificación

Ensayo real de una superior de seis conexiones: ejecución de las trece etapas desde su STL bruto, ocho vistas, herramienta B4D de cemento comprobada, primaria y supra cerradas, un componente cada una, solapamiento cero y perímetros funcionales conservados antes y después de exportar. Alturas medianas en las secciones: anterior 6,42 mm, posterior 5,08 mm; mínimo oclusal muestreado 5,09 mm. Son resultados de ese ensayo, no valores universales ni una aprobación del laboratorio.

Las pruebas automatizadas usan figuras sintéticas y datos temporales: autenticación, aislamiento de archivos, ausencia de fotogramas inventados, errores y correcciones visibles antes de terminar, instrucciones de altura/espesor independientes y detección de una supra cerrada pero demasiado fina.
