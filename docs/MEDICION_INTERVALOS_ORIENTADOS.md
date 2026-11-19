# Cruces interiores del STL y medida de paredes

Corrección del supervisor, 17/09/2026. No modifica el original, primaria, supra,
cemento, conexiones, retenciones ni umbrales de aceptación.

El original del caso `ID_PRIVADO_NO_PUBLICADO` contiene superficies
orientadas solapadas en algunas regiones. Ser cerrado y tener orientación
consistente no descarta esos autosolapes. En dos rayos del primer intento del
trabajo `ID_PRIVADO_NO_PUBLICADO`, el número de vueltas orientado del
original fue 1 → 2 → 1 → 0. La primera cara interior tiene normal entrante y no
es la salida del volumen ocupado.

En el intento 01 del trabajo `ID_PRIVADO_NO_PUBLICADO`, una sonda cuya
entrada en supra está en `[-19.2634148134, -9.4441967133, 1.9257042325]` devuelve
cruces a 1.363923, 1.364082, 1.365122, 2.755549 y 6.936912 mm, con signos
`- + + - +`. La salida del primer intervalo positivo es 1.365122 mm: después
hay un hueco real. El control anterior registraba cero al encontrar primero la
cara entrante interior. No corresponde tomar la última superficie a 6.936912 mm.

`ray_material.first_material_exit` recupera la ocupación orientada a partir de
los cruces hasta el exterior y devuelve la primera transición de material
positivo a vacío. Una sonda que parte fuera del material, una normal tangente o
datos inválidos no dan una salida válida. El control de tres líneas y el control
de paredes utilizan el mismo método; las mediciones no válidas siguen pendientes.

Las pruebas incluyen volúmenes solapados con una pared de 3.8 mm, otra de 0.4 mm
que debe seguir fallando, un hueco seguido por material distante, una chimenea
inclinada, retenciones, paredes laterales y ausencia de supra. La revisión real
del intento 01 conserva dos sondas finas (0.179 y 0.685 mm), 717 muestras laterales
finas y 125 sin cavidad; esta corrección no aprueba esa geometría. El informe
original de cada intento permanece intacto y las relecturas llevan nombres de
diagnóstico separados.

Este cálculo interpreta volumen orientado positivo. No repara autosolapes,
certifica espesores globales ni valida la fabricación. Las versiones anteriores
ya copiadas en un expediente conservan su propio verificador: no atribuirles
esta corrección ni sustituir sus informes. Una nueva ejecución debe registrar
los hashes de los módulos actuales y volver a comprobar la geometría resultante.
