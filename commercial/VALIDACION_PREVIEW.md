# Evidencia de la preparación del 11/09/2026

La instalación del laboratorio conserva el commit `2bab22b` y versión 0.5.2; repositorio instalado limpio y `/health` responde `ok` en localhost y en CAD-CAM. No se ha cambiado código del motor/panel instalado, configuración, datos, servicio, firewall ni acceso directo.

Código inicial de la preview: `9bc59bff15e6665065d31bfe321f8a8567122368`. [Compilación GitHub](https://github.com/piguin40-eng/segment-iq/actions/runs/34575289011): **correcta** para Windows x64, macOS x64 y macOS arm64, con tres pruebas de política del cliente en cada job. Estos enlaces requieren acceso al repositorio privado y los artefactos tienen retención limitada; no son todavía un portal público de distribución.

El ejecutable empaquetado Windows también se ha probado localmente: ventana nativa, conexión a un servidor sintético, puente IPC solo en el formulario local, ausencia de Node/IPC en página remota, rechazo de HTTP LAN, bloqueo de navegación/tráfico fuera del origen y cierre correcto. Las pruebas no usaron casos reales ni pidieron trabajo al servidor instalado. No se ha probado una instalación completa en Windows limpio, ni la interfaz del cliente en hardware Mac, ni dictado real en cada plataforma.

| Instalador de evaluación | SHA256 |
|---|---|
| Windows x64, build local probado | `HASH_PRIVADO_NO_PUBLICADO` |
| Mac Apple Silicon, CI | `HASH_PRIVADO_NO_PUBLICADO` |
| Mac Intel, CI | `HASH_PRIVADO_NO_PUBLICADO` |

La firma Authenticode de Windows devuelve **NotSigned**. Los builds Mac de esta pipeline no usan credenciales Developer ID ni notarización. No son entregas de producción; firmar/notarizar requiere cuentas/certificados del titular.

`pnpm audit` devolvió cero avisos conocidos en esta consulta del árbol de dependencias del escritorio. No cubre el motor, los modelos ni una prueba de penetración. Se han generado inventarios separados de Python: 57 paquetes del agente y 17 del entorno geométrico; su licencia procede de metadatos sin revisión jurídica. Las dependencias y licencias de Electron/Chromium siguen necesitando conservación y revisión en cada release.

El control de evidencias comercial tiene tres pruebas unitarias y devuelve correctamente `BLOCKED_FOR_SALE` con los quince requisitos pendientes. No se ha activado la suscripción ni obtenido permisos sanitarios.

La pipeline de pruebas ya existente detectó inicialmente dos fallos por ausencia de SciPy en su entorno de GitHub (86 pruebas pasadas, 10 omitidas). Se ha añadido la instalación de `requirements-geometry.txt` **solo al runner de pruebas de esta rama**, sin tocar los entornos instalados del laboratorio. Consultar el resultado posterior de Checks en la rama para su estado final.
