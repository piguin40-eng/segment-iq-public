# Puente de tres piezas: referencia del laboratorio

## Alcance y recuperación

Identificador de aprendizaje: **LAB-PUENTE-3U-20260915**. Puente superior 14–15–16 sobre dos implantes, aportado el 15 de septiembre de 2026. El usuario pide copiar su diseño terminado para estudiar su forma y conservarla como referencia. Esa copia está autorizada y debe acreditarse como trabajo del laboratorio. Una construcción independiente posterior debe salir de las entradas de su propio caso.

Buscar en el RAG `LAB-PUENTE-3U-20260915 cuellos encía puente 14 15 16`. El documento privado `Aprendizaje_LAB-PUENTE-3U-20260915.md` proporciona las rutas del original, escena, medidas y vistas. El STL de referencia tiene SHA256 `HASH_PRIVADO_NO_PUBLICADO`. Conservar los modelos e imágenes del caso en el almacén privado; la skill reutilizable contiene el método y el identificador.

## Qué cambia al seguir esta referencia

- **Objetivo morfológico:** usar este puente del laboratorio al comparar la forma de 14–15–16. Nuestra revisión v009 con encía fue rechazada explícitamente («esa encia sta fatal»); no recuperarla del historial como ejemplo positivo ni asumir que conservar la colocación manual anterior equivale a alcanzar el resultado nuevo.
- **Cuellos y transición cervical:** en las vistas de la referencia, la superficie externa continúa desde la corona hacia la zona cervical, conservando la identidad de cada diente. Nuestra v009 presenta sobrevolumen en forma de collares y un borde irregular con facetas visibles. Para una nueva propuesta, trabajar el contorno cervical y las transiciones interproximales sobre el escaneo; comprobar la silueta desde vestibular, palatino y basal. Añadir un manguito uniforme o cambiar su color no reproduce esa forma.
- **Anatomía y arcada:** la referencia conserva cúspides/surcos, dos premolares diferenciados y una corona molar de mayor tamaño. Comparar forma, inclinación y continuidad del arco con los dientes vecinos, incluida la relación 13–14, usando vistas coincidentes. La proximidad visual no demuestra un contacto interproximal medido.
- **Relación con tejidos y antagonista:** evaluar el diseño con el escaneo superior y con el antagonista en su registro original. Medir los cambios por región antes/después; no corregir el reborde moviendo indiscriminadamente todas las coronas ni deducir un espesor oclusal a partir del volumen total. La nueva referencia sustituye el objetivo de forma anterior, pero su recepción no demuestra ajuste clínico o espesor mínimo.
- **Conexiones:** mantener íntegros asientos, periferia funcional y canales. El usuario indicó 15 angulado y 16 recto. La propuesta anterior del agente de 30°/AB-SR-01 no es una especificación confirmada del nuevo STL. Recuperar el ángulo/variante de sus fuentes cuando sea necesario; la coincidencia de la banda inferior común no identifica toda la conexión.

Estas observaciones visuales están documentadas por el agente a partir de un ejemplo del usuario. No convierten automáticamente la forma cervical, altura, radio o proporciones del ejemplo en requisitos para todos los pacientes. Usar cada nuevo diseño y las correcciones vigentes como datos principales.

## Lección de orientación: no interpretar una superposición sin registro

Este STL fue exportado en una orientación diferente a la de los escaneos originales. Importarlo con identidad mostraba las coronas hacia la encía. Se resolvió una transformación rígida con los centros de dos anillos de asiento y sus ejes, comprobada después contra puntos de la banda funcional inferior de la biblioteca local.

`Registro_rigido_referencia.json` conserva la matriz `matrix_reference_to_original_scans`. Aplicarla solo a la copia de visualización de este STL; no mover los escaneos/implantes originales, no escalar y no reutilizar esta matriz en otro caso. La distancia entre centros fue 6,431495 mm y el residuo máximo de centros 0,0000063 mm. La distancia máxima de los puntos de comprobación a la malla fue 0,00445 mm. Son resultados de registro de este ejemplo, no tolerancias clínicas generales. La comprobación de esa banda no certifica toda la interfase.

Para otro archivo, identificar referencias funcionales propias y conservar su matriz y residuos. La caja envolvente parecida no garantiza un registro común; tampoco basta una PCA sin verificar sentidos/ejes. Comparar morfología, contactos u oclusión solo después de verificar el registro.

## Lo que el STL permite y lo que falta

La copia contiene una malla cerrada, una componente, 109.408 triángulos y volumen 1.148,170 mm³ bajo la convención de milímetros del caso. Es una comprobación geométrica, no una aprobación de fabricación. El STL no declara unidades, materiales, separación diente/encía ni historial de herramientas; el color marfil de las vistas es solo visualización. No concluir «el laboratorio no utiliza encía» ni inventar un límite rosa/blanco a partir de este archivo.

Un resultado terminado enseña la forma obtenida, no demuestra los movimientos de Blender for Dental ni los valores usados. Para reproducir los pasos, recurrir a escenas, código y grabaciones identificadas. Mantener como pendientes oclusión medida, espesores y validación del diseño cuando no exista evidencia específica.

## Aplicación en el siguiente intento

1. Recuperar la referencia y abrir sus vistas, el STL y el registro, conservando la autoría.
2. Partir del caso nuevo o de la entrada autorizada; registrar anatomías, tejidos, implantes y antagonista sin perder la colocación del técnico.
3. Ajustar arcada, contactos y oclusión; desarrollar después el contorno cervical con transiciones continuas y sin los collares rechazados. Si se necesita encía protésica, definir su geometría y límite desde los tejidos y el objetivo del caso, no desde una banda de color uniforme.
4. Guardar antes/después con la misma cámara, cortes y medidas por región. Un remallado cerrado o normales suaves no resuelve por sí mismo un error de forma.
5. Presentar el puente para revisión del laboratorio; en este caso la segmentación de barra va después de validar el puente. Conservar correcciones pendientes y evidencias, sin declarar aprendizaje universal ni entrenamiento de pesos por guardar una referencia.
