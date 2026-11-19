# Permisos, licencias y mercados

Documento preparatorio, no dictamen de clasificación ni expediente aprobado. Consultado el 11/09/2026. La finalidad propuesta es ayudar a profesionales a separar un diseño dental STL en primaria y supra, conservar conexiones y generar revisiones para evaluación humana. Antes de vender hay que precisar indicaciones, usuarios, entradas, salidas, contraindicaciones, materiales y límites.

## España y Unión Europea

La clasificación del software depende de su finalidad prevista y funciones, no de que se presente como “asistente” o se ejecute localmente. Hay que evaluar SEGMENT IQ frente al MDR, sus accesorios y las reglas aplicables; no asigno clase I, IIa o una exención sin ese análisis. El motor calcula geometría específica de una prótesis: esto exige una evaluación real. Fuente: [MDCG 2019-11 rev.1, junio de 2025](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf).

Según la clasificación y rol resultantes, preparar documentación técnica, gestión de riesgos/calidad, evaluación y validación, información al usuario, vigilancia y procedimiento de conformidad. Determinar con el responsable regulatorio si interviene un organismo notificado, PRRC, UDI/registros y qué obligaciones corresponden al fabricante del software frente al laboratorio que fabrica la prótesis. No confundir la condición de producto dental a medida con una exención del programa vendido a muchos laboratorios. En España revisar la licencia de funcionamiento aplicable y la autoridad competente: [AEMPS, instrucción PS 1/2025](https://www.aemps.gob.es/productosSanitarios/docs/instruccion-ps-1-2025-licencia-previa.pdf).

El mapa debe incluir el Reglamento de IA y su calendario vigente. La Comisión publica cambios recientes de aplicación; verificar el texto consolidado aplicable a este producto antes de fijar plazos contractuales. Fuente: [marco europeo de IA](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai). No activar cambios globales del motor después de cada vídeo sin validación, trazabilidad y control de versión.

Evaluar también el alcance del Cyber Resilience Act por módulo y sus exclusiones para productos sujetos a regulación sectorial. No sumarlo automáticamente al MDR ni asumir exención de todo el escritorio. La Comisión sitúa las obligaciones de notificación aplicables desde 11/09/2026 y las principales desde 11/12/2027. Fuentes: [resumen del CRA](https://digital-strategy.ec.europa.eu/en/policies/cra-summary), [notificaciones](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting).

## América: aprobación país a país

No existe un único permiso válido para América. La autorización europea no concede automáticamente la de otro país. El lanzamiento debe usar una lista explícita de países habilitados; los demás siguen pendientes.

| Mercado | Autoridad/tema a analizar | Decisión pendiente |
|---|---|---|
| Estados Unidos | FDA, software/dispositivo y eventual vía de comercialización; privacidad federal/estatal | Clasificación y necesidad de presentación, registro y representante. El código dental NOF es una referencia, no una clasificación atribuida a SEGMENT IQ |
| Canadá | Health Canada, definición y clasificación de SaMD | Clase, licencias y obligaciones del fabricante/importador |
| México | COFEPRIS, software como dispositivo médico | Registro, representante/importador, etiquetado y expediente local |
| Brasil | ANVISA, SaMD | Aplicabilidad de RDC 657 y demás reglas actuales, regularización y responsable local |
| Resto de América | Autoridad sanitaria y ley de datos de cada país seleccionado | Investigación local antes de habilitar venta; no declarado cubierto |

Fuentes oficiales: [FDA, clasificación dental CAD/CAM de referencia](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm?ID=NOF), [Health Canada, guía SaMD](https://www.canada.ca/en/health-canada/services/drugs-health-products/medical-devices/application-information/guidance-documents/software-medical-device-guidance.html), [COFEPRIS, guía de registro](https://www.gob.mx/cofepris/documentos/guia-para-la-obtencion-del-registro-sanitario-de-dispositivos-medicos?state=draft), [ANVISA, preguntas sobre SaMD](https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2022/software-como-dispositivo-medico-perguntas-e-respostas/perguntas-respostas-rdc-657-de-2022-v1-01-09-2022.pdf). Validar vigencia de las referencias antiguas al tramitar en cada país.

## Derechos sobre dependencias y aprendizaje

| Componente | Preparación requerida |
|---|---|
| Código propio | Identificar titular, colaboradores y cesiones; delimitar la licencia de cada módulo. Repositorio privado no equivale a titularidad probada |
| Blender y scripts/add-ons | Revisar GPL y obligaciones de distribución/código fuente según integración concreta. No prometer cerrar todo el código ni cambiar licencias existentes |
| Blender for Dental | No redistribuido en el cliente. Solicitar confirmación escrita para integración automatizada, ejecución desatendida, servidores/licencias por laboratorio y uso de formación/corpus. Comprar un módulo no acredita por sí solo todos esos derechos |
| Tissue y otros add-ons | Inventariar versión, autor, licencia y código efectivamente usado; conservar avisos y fuentes exigibles |
| Electron/Chromium/Node | Incluir avisos que acompañan la distribución y auditoría de versiones/dependencias. No quitar LICENSE.electron.txt ni LICENSES.chromium.html |
| Python, FFmpeg, OCR, voz, embeddings, geometría | Inventario por entorno/binario real; verificar bibliotecas transitivas y licencias de códecs/modelos. Los metadatos automáticos no son autorización jurídica |
| OpenAI/Codex | Autenticación/coste/contrato por cliente o servicio comercial propio. Nunca copiar la sesión ChatGPT, tokens o claves de este laboratorio a compradores |
| Vídeos, cursos y diseños RAG | Registro de titular, autorización de indexación/uso comercial, alcance, fecha y retirada. Biblioteca privada por defecto; material de un cliente no pasa a otro sin base válida |
| Marca SEGMENT IQ | Búsqueda de antecedentes y viabilidad en OEPM/EUIPO y países objetivo, clases pertinentes y titular. Aún no se ha realizado una búsqueda de disponibilidad |

Referencias para la revisión: [Blender, licencia](https://www.blender.org/about/license/) (la consulta automática no pudo recuperar esta página; revisión del texto pendiente), [Blender for Dental, módulos y condiciones enlazadas](https://www.blenderfordental.com/), [autenticación oficial de Codex](https://learn.chatgpt.com/docs/auth), [Electron, seguridad](https://www.electronjs.org/docs/latest/tutorial/security). Las condiciones contractuales completas de B4D no han quedado verificadas; no se ha otorgado ninguna licencia comercial desde este trabajo.

## Firma e instalación

Identificar primero al titular legal. Preparar firma Authenticode de Windows mediante proveedor/certificado válido y sello de tiempo; comprobar firma del instalador y binarios. Para macOS, cuenta Apple Developer, Developer ID, hardened runtime, notarización y stapling, más pruebas de Gatekeeper. No usar certificados autofirmados como sustituto comercial. Fuentes: [Microsoft, opciones de firma](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options), [Apple, Developer ID](https://developer.apple.com/developer-id/).

La firma acredita origen e integridad técnica; no acredita aprobación sanitaria, cumplimiento RGPD o derechos sobre B4D.
