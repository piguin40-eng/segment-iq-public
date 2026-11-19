# Acceso al laboratorio

El panel pide usuario y contraseña. Se configura una cuenta del laboratorio; no hay administración de múltiples usuarios o roles.

## Servidor persistente en Windows

Desde 0.3.3, `Install-Service.ps1` registra la tarea de Windows **SEGMENT IQ - Servidor del laboratorio** con el usuario conectado, sin guardar su contraseña de Windows. Arranca al iniciar sesión y mantiene un supervisor que recupera el servidor tras una salida inesperada: espera inicialmente cinco segundos y aumenta hasta un minuto, con un máximo de diez fallos rápidos consecutivos. Windows añade recuperación del supervisor, con un minuto entre intentos. No depende de mantener una terminal abierta. Ejecutar una vez desde la carpeta app:

```powershell
.\Install-Service.ps1 -InstallRoot "$env:USERPROFILE/Documents/DentalLabAgent"
```

`Install-Lab.ps1 -StartAtLogin` también instala esta tarea. El mismo acceso directo sigue funcionando y arranca la tarea si el panel no responde. Se conservan las credenciales y los datos existentes. Los registros persistentes están en `data/logs/service.log` y `data/logs/service.err.log`; el segundo incluye errores nativos de Python cuando pueden capturarse.

«No se puede conectar con SEGMENT IQ» indica que el navegador no llega al servidor: comprobar el equipo anfitrión, su acceso directo y la red. «Usuario o contraseña incorrectos» indica que sí se llegó al servidor y el acceso fue rechazado. Reiniciar el servicio requiere iniciar sesión de nuevo; no elimina los casos ni sus archivos. Una ejecución interrumpida se señala para revisión y no se reinicia silenciosamente como un caso nuevo.

## Cuenta del laboratorio

En una instalación nueva, el usuario inicial es `admin` y la contraseña inicial es la clave aleatoria del campo `password` en `data/config.local.json`. Al actualizar una instalación anterior, se conserva esa clave y se incorpora el usuario `admin` si todavía no estaba configurado.

Para elegir usuario y contraseña, ejecuta desde la carpeta `app` con el Python instalado:

```powershell
../runtime/python/Scripts/python.exe -m dental_lab.cli set-login --username NombreDelTecnico
```

El comando solicita la contraseña dos veces sin mostrarla ni pasarla como argumento. Respeta `DENTAL_LAB_DATA` si la instalación usa otra carpeta. Reinicia SEGMENT IQ después del cambio; el reinicio cierra las sesiones anteriores.

La configuración privada guarda `username` y `password_hash` (PBKDF2-HMAC-SHA256, 600.000 iteraciones, sal aleatoria de 16 bytes). El campo histórico `password` se conserva como clave Bearer para la API y OpenClaw; cambiar el acceso web no cambia esa clave. La contraseña web personalizada no se guarda en texto legible.

`POST /login` recibe JSON con `username` y `password`. El usuario ignora mayúsculas y espacios exteriores; la contraseña se compara exactamente. El acceso crea una cookie HttpOnly, SameSite Strict, válida durante 12 horas, con Secure cuando se utiliza HTTPS. Se admiten hasta 10 intentos por minuto e IP. Cerrar sesión invalida su cookie en el servidor.

La configuración, las claves, las cuentas del laboratorio y los datos permanecen fuera de GitHub y del ZIP del código.
