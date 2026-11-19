---
name: blender-barras-video
description: Construir o corregir barras primaria/supra siguiendo el vídeo del laboratorio Blender Barras, desde la orientación y los conos hasta el cúter, seguridad, cemento y exportación. Consulta obligatoria en la planificación y revisión de segmentaciones de SEGMENT IQ.
---

# Barras del laboratorio · protocolo del vídeo

Versión 1.0.0 · referencia `LAB-VIDEO-BARRAS-20260916`.

el laboratorio pidió el 16/09/2026 incorporar este vídeo como patrón obligatorio de SEGMENT IQ. Leer [procedimiento](references/procedimiento.md) y [evidencia y límites](references/evidencia.md) antes de planificar y al revisar una barra. El protocolo se aplica a nuevas segmentaciones y correcciones; no a tareas ajenas a geometría.

## Prioridad y alcance

Seguir el orden de construcción del vídeo, adaptando las medidas al STL original del caso. Las correcciones posteriores del laboratorio prevalecen sobre preferencias incompatibles del ejemplo. Sigue vigente el criterio de el laboratorio: barra recta y expulsiva según el eje de inserción, sin socavaduras, más estrecha y con menos espesor de metal, preservando el contorno de la secundaria y el perímetro funcional completo de las conexiones. «Recta» permite seguir el arco en planta y un plano de referencia inclinado; no significa imponer Z global ni igualar ejes de implantes divergentes.

El vídeo muestra seis tubos en un ejemplo de arcada: no exige seis implantes en otros casos. No copiar coordenadas, geometrías terminadas, alturas ni número de clics. Registrar la transformación del caso, medir cada chimenea y distinguir su eje de la dirección de inserción de la secundaria. En canales angulados, verificar la trayectoria real; no prolongar sin límite el eje del asiento como si toda la chimenea fuera recta.

## Secuencia que hay que justificar

1. `orientacion`: importar el original, Enter Target, cuatro puntos, Align y bloqueo; comprobar el sistema de coordenadas antes de iBar.
2. `tubos_conos`: Start and name HYBRID; crear cada tubo desde la chimenea, editar radios/altura con rayos X y construir los conos que protegen la conexión.
3. `mascara_trazado`: Create Mask Protection antes de dibujar; contorno cerrado, sin cruces ni invasión de zonas funcionales, incluyendo extremos distales.
4. `plano_barra`: Make Basic Design → orientar vista → Extrude DESIGN → ajustar plano y altura → Cut the DESIGN. Conservar cuerpo continuo y región basal antes de angular. Medir rectitud y metal real.
5. `remesh_cuter`: Remesh Design into CUTTER; esperar a que termine y seleccionar el objeto correcto.
6. `afinamiento`: retocar el cúter hacia dentro donde invade la secundaria; proteger chimeneas, mantener expulsividad y contorno. Suavizar y salir explícitamente del modo Smooth.
7. `seguridad`: Add Safety Zone → revisar → Accept → Correct Thickness of Hybrid. Priorizar corregir el cúter; no engordar automáticamente la anatomía aprobada para esconder una invasión del metal.
8. `cemento_separacion`: Adjust Cement Space → comprobar valor/unidades → Separate Hybrid; medir gap y preservar conexiones.
9. `retenciones`: justificar su tratamiento. Este vídeo comenta retenciones locales opcionales; no demuestra una retícula automática obligatoria. Rechazar cualquier retención que contradiga la inserción o el espesor de la secundaria. Si otro patrón del caso las requiere, medirlas y citar esa fuente.
10. `comprobacion_exportacion`: inspeccionar secciones, primaria, supra y chimeneas; exportar cada pieza con Selection Only y reimportar sin desplazar para comprobar alineación.

## Aplicación en el agente

El supervisor de SEGMENT IQ carga esta skill y sus referencias directamente, fuera de la selección top-k del RAG. En PLAN, explicar cómo se realizará cada paso sobre este caso. En REVISIÓN, aportar archivos/medidas y dejar pendiente lo no comprobado. El supervisor exige el identificador de versión, hash y una respuesta por cada paso; esos recibos acreditan contexto y respuesta, no la exactitud clínica de la malla.

Usar Blender for Dental instalado y licenciado cuando la operación esté disponible. Identificar por etapa qué ejecutó B4D y qué construyó SEGMENT IQ. Actualmente el adaptador del producto acredita solo la herramienta de cemento de iBar mediante `B4D_ejecucion.json`; esta skill no añade por sí sola los demás operadores B4D. Una etapa numérica equivalente debe declararse como tal, con comprobaciones, nunca como clics B4D realizados.

Construir desde el STL original, conservar intentos y comparar la geometría anterior con la nueva. No presentar un plan o una recuperación del RAG como segmentación ejecutada. Si una operación falta en las herramientas permitidas, registrarla como pendiente concreta; no sustituir resultados anteriores ni inventar un recibo. No pedir un JSON al técnico para eludir la preparación automática.

## Resultado revisable

Conservar perfil medido, escenas intermedias, registro B4D, cortes y medidas de altura/anchura/espesores, comprobación de conexiones y trayectoria de extracción. Entregar primaria y supra por separado en las coordenadas originales. La malla cerrada, el color del objeto o la aceptación de Safety Zone no demuestran ajuste, resistencia ni ausencia global de socavaduras. Mantener la aprobación final del laboratorio pendiente hasta revisión expresa.
