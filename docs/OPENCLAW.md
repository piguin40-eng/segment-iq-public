# Conectar con OpenClaw

El servicio SEGMENT IQ funciona de forma independiente. Para un agente OpenClaw, copiar el contenido de `openclaw/` a un workspace propio y registrar ese workspace:

```text
openclaw agents add dental-lab --workspace "D:/Agentes/dental-lab" --non-interactive
openclaw agents set-identity --workspace "D:/Agentes/dental-lab" --from-identity
```

Configurar el modelo y permisos de ejecución según la instalación OpenClaw real. No compartir canales del laboratorio ni sobrescribir otro agente por defecto. La skill explica cómo consultar SEGMENT IQ y generar con su motor. OpenClaw necesita acceso a este PC o a la API LAN con la clave del laboratorio; una instancia en otro equipo no ejecuta Blender aquí por el mero hecho de copiar la skill.

Estas órdenes proceden de la [documentación oficial de agentes OpenClaw](https://docs.openclaw.ai/cli/agents), consultada el 08/09/2026. No se ha instalado OpenClaw en CAD-CAM. Desde 0.5, la generación puede utilizar Codex con sus herramientas y revisión; el chat del RAG sigue usando Ollama. Ver [arnés de ejecución](ARNES_CODEX.md).
