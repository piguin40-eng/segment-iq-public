# Motor propio: ejecutar, adaptar y comprobar

## Qué se entrega

Código Python que crea trazado, perfiles, conos y retenciones desde el STL bruto. No carga los .blend del laboratorio, sus cutters ni las mallas terminadas. El motor utiliza Blender 3.6, Tissue y operaciones booleanas de manifold3d. Desde 0.4 admite ejecutar la herramienta real de cemento de Blender for Dental instalado mediante un adaptador propio, sin redistribuir código propietario. Ver [VISOR_Y_B4D.md](VISOR_Y_B4D.md) para el alcance concreto. Los historiales del usuario se conservan como documentos de aprendizaje; no deben ejecutarse como macros.

El perfil INF incluido reproduce la construcción propia ensayada el 7 de septiembre de 2026. No es una reproducción literal completa del complemento: el control de seguridad es una adaptación geométrica. El resultado independiente seguía pendiente de aprobación de forma por el laboratorio. No confundirlo con su inferior terminada de referencia.

## Preparación y ejecución

Desde 0.3, el panel ejecuta primero engine/prepare_profile.py. No pide al técnico el perfil JSON. Ver PREPARACION_AUTOMATICA.md. Las instrucciones manuales siguientes sirven para desarrollo y reproducción histórica.

Python externo con las dependencias de `requirements-geometry.txt` en la raíz del proyecto; Blender 3.6 con `mesh_tissue`. Las bibliotecas Python externas no se instalan dentro de Blender: este usa su numpy incorporado. El paquete fue probado en Windows con Blender 3.6.5. No se ha ensayado en Linux ni dentro del agente OpenClaw del usuario.

Desde la raíz del proyecto, emplear rutas absolutas para entrada, perfil, Blender y carpeta nueva de ejecución:

```powershell
python engine/ejecutar.py --input "D:/Casos/entrada.stl" --profile "D:/skill/profiles/caso.json" --run-dir "D:/Casos/ensayo_001" --blender "C:/Program Files/Blender Foundation/Blender 3.6/blender.exe" --check
```

Quitar `--check` para construir. `--until 3` genera hasta el diseño básico. Cada ejecución exige una carpeta nueva, no sobrescribe intentos. Los nombres internos conservan INF por compatibilidad con el prototipo; no deducir la arcada a partir de ellos. `--python-deps` es opcional para un directorio de bibliotecas ya instalado; preferir un entorno virtual normal.

## Orden y decisiones geométricas

| Etapa de código | Trabajo propio | Qué comprobar |
|---|---|---|
| 01 | Importación, transformación y bandas radiales del STL | Escala en mm, orientación, límites completos y extremos distales |
| 02 | Candidatos circulares y ajuste de ejes | Conteo, centros, radios y correspondencia con asientos reales |
| 03 | Tubos, conos, trazado proyectado y seis perfiles | Cobertura de toda la arcada; altura y profundidad; no acabar en el último implante |
| 04 | Unión del núcleo y conos | Sólido continuo, zonas de conexión cubiertas |
| 05 | Remallado, suavizado y dos superficies ±gap/2 | No perforar la supra ni invadir asientos; seguridad adaptada |
| 06 | Intersección/resta con el STL del caso | Primaria y supra completas; regiones y canales previstos |
| 07 | Selección de superficie para retenciones | Grosor disponible y exclusión alrededor de conexiones |
| 08 | Decimate → dual → aristas → subdivisión → Shrinkwrap → Skin → Subsurf → remesh → smooth | Red nacida de la superficie actual, sin plantillas importadas |
| 09 | Protección de canales y resta de retenciones | No dañar tubos ni reducir indebidamente la sección |
| 10 | Limpieza limitada de primaria | Cierre y topología esperada, sin ocultar pérdida de anatomía |
| 11 | Comprobaciones y exportación en coordenadas originales | Solapamiento, anillos de conexión y distancias muestreadas |
| 12 | Escenas de antes/después, ensamblada y separada | Revisión visual, en especial extremos y altura/profundidad |
| 13 | Recarga de los STL exportados | Cierre, orientación y topología tras exportación |

Después de la etapa 13 el ejecutor aplica controles que pueden fallar, no solo imprime métricas. PASS significa controles geométricos superados; la revisión del diseño permanece PENDING. No se calcula todavía el espesor mínimo global, la trayectoria de inserción, la oclusión ni la cobertura anatómica diente por diente. Las distancias de interfaz incluyen retenciones: no prueban un hueco uniforme de cemento.

## Parámetros específicos del ejemplo

El perfil identifica el STL por SHA256. Ocho conexiones de radio 2,4 mm; trazado con centro radial X=0/Y=25 en el marco orientado, 38 muestras por borde y percentiles radiales 30/70; TOP Z=0,3; conos a Z=0,1 salvo el segundo a -0,5; cemento 0,14 mm. El segundo cono se ajustó para evitar una ventana; no es una regla anatómica transferible. Las conexiones se ordenan por ángulo: “2” significa índice del detector, no número dental.

En código permanecen constantes del prototipo que hay que revisar al adaptar: bandas angulares 0,055 rad; rango angular percentiles 1,2/98,8; suavizado de radios sigma 1; origen de rayos Z=-30 y cierre Z=-35; subdivisión del trazado tres veces; perfiles MARGIN -0,25, Attach 0, INSIDE +0,2, Flat +0,4, Extrude +0,9 respecto al trazado; conos con radios asiento+0,65 y asiento+0,25; remesh 0,15; Smooth 0,5 ×10. El detector filtra radios 0,45–3,7, normal Z con |Z|≥0,5 y tolerancias de circularidad/planitud específicas. La preparación automática admite radios individuales medidos; el detector heredado conserva radio único.

Retenciones: selección con normal Z≥0,6, espesor por rayo ≥0,9 mm, distancia al original ≥0,045 y exclusión radial ≥3,3; Decimate 0,015; Shrinkwrap +0,1; Skin radio 0,325; Subsurf 2; voxels 0,2/0,1; Smooth 0,5 ×5; protección de ejes con cilindros de radio 3,2 y longitud 60. Son parámetros de esta adaptación, no todos recuperados del historial original. Desde 0.3 las protecciones usan el radio individual más 0,9 y 0,8 mm, respectivamente. Son márgenes de propuesta, sujetos a revisión.

## Adaptar un caso nuevo sin copiar geometría

1. Inspeccionar el STL bruto y las referencias disponibles. Registrar unidades, arcada, asientos, límites y medidas que se puedan recuperar. Mantener referencias geométricas fuera del motor de generación.
2. Crear un perfil nuevo a partir de la plantilla, medir los valores vacíos y definir la transformación raw_to_work. El marco debe situar X=0 en el centro radial y +Z hacia oclusal. No aplicar escala. Registrar el hash del STL y explicar en adaptation_notes de dónde procede cada medida.
3. Construir y revisar el trazado propio. El algoritmo radial es un punto de partida para esta forma en U; si excluye una pieza distal o cruza anatomía, sustituirlo por un trazado nuevo calculado/proyectado sobre el STL actual. No importar DrawingDone de otro trabajo.
4. Ajustar altura y profundidad con secciones locales de la barra, no solo volumen total. Mantener toda la pieza 37 en esta inferior; revisar el extremo correspondiente en cada otra arcada. Conservar asientos y ejes medidos.
5. Revisar el control de seguridad y conexiones antes del cemento. Si se precisa Zone2Add/selecciones específicas del laboratorio, reconstruirlas del caso con herramientas propias o B4D instalado y documentar la etapa real; el checkpoint 05 del motor no demuestra ese procedimiento literal.
6. Regenerar, inspeccionar y registrar las métricas con los umbrales definidos para el caso. No aumentar tolerancias ni borrar piezas para forzar PASS. Confirmar visualmente que la forma responde a lo pedido antes de entregar.

La plantilla vacía no es un fallo de instalación: evita aplicar sin medición la anatomía del ejemplo a otro paciente. El agente debe completar la adaptación mediante su trabajo, no pedir al usuario que le entregue la segmentación.

## Evidencia y procedencia

El ejemplo previo obtuvo primaria 1387,3785 mm³ y supra 5336,5888 mm³, ambas cerradas y de un componente con ocho canales; solapamiento 0 mm³. El muestreo de anillos dio errores inferiores a 0,000001 mm. Son mediciones numéricas del ensayo, no tolerancias universales. Consultar los JSON y el registro de prueba portable del paquete para el estado real de cada ejecución.

Las escenas del laboratorio enseñaron que la barra debía tener más altura y profundidad. Los ensayos R2–R4 no son patrones aceptados. La revisión que reparó/copió geometría terminada no es una construcción propia. Los dos historiales originales difieren: el limpio elimina repeticiones geométricas significativas; leer historial-movimientos.md antes de reconstruir la secuencia histórica.

La prueba portable volvió a generar las trece etapas desde una carpeta vacía. La primaria antes de retenciones y la supra coinciden en volumen con el ensayo anterior dentro de 0,001 mm³. La retención regenerada cambia: elimina 16,1098 mm³ frente a 17,8072, y la primaria nueva mide 1389,0759 mm³. Pasa los controles, pero no es una reproducción idéntica de la malla. No se ha aislado la causa exacta de esa variación procedural; comparar siempre la red y el resultado en cada ejecución y conservar el código y los archivos generados.
