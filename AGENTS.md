# Guía de Trabajo para Agentes (AGENTS.md): juanchito-assitant

Bienvenido a **juanchito-assitant**, el generador inteligente y adaptador de currículums para [resume.lol](https://resume.lol) liderado por Mateo Pissarello (`@MateoPissarello`).

Cualquier agente que trabaje en este repositorio DEBE seguir estrictamente las siguientes directrices operativas.

---

## 1. Principio Fundamental: Pair Programming Activo

> [!IMPORTANT]
> **Prohibido el desarrollo en piloto automático**:
> - Nunca generes archivos ni módulos masivos sin antes discutir su arquitectura, firma y propósito con Mateo.
> - Este proyecto se construye **conjuntamente**. Plantea opciones, explica los trade-offs y permite que Mateo decida o escriba partes del código.

---

## 2. Actualización Automática del Logbook

> [!NOTE]
> Cada agente es responsable de mantener actualizado el archivo [`LOGBOOK.md`](./LOGBOOK.md):
> 1. **Al iniciar una discusión de un hito**: Cambiar su estado a `DISCUSSING` y agregar una entrada en la bitácora con los temas abordados.
> 2. **Al implementar**: Cambiar su estado a `IN_PROGRESS` mientras se codifica y prueba.
> 3. **Al finalizar**: Cambiar el estado a `COMPLETED`, registrar las decisiones tomadas y la evidencia de pruebas ejecutadas.

---

## 3. Comandos Operativos de Flujo (Workflow)

El agente debe responder a los siguientes comandos emitidos por Mateo:

- **`-handshake`**:
  1. Lee inmediatamente [`LOGBOOK.md`](./LOGBOOK.md) y [`AGENTS.md`](./AGENTS.md).
  2. Identifica el último hito completado y el hito activo actual.
  3. Responde con un saludo amigable y un resumen ejecutivo conciso:
     - Estado del proyecto.
     - Último hito completado.
     - Hito actual por abordar.
     - Pregunta de alineación para continuar.

- **`-discussion`**:
  1. Abre una sesión de diseño colaborativo para el hito activo o propuesto.
  2. Plantea los requerimientos técnicos, alternativas de diseño y estructura de datos.
  3. Registra las conclusiones en [`LOGBOOK.md`](./LOGBOOK.md) bajo el estado `DISCUSSING`.

- **`-checkpoint`** (o `-log`):
  1. Registra el avance actual en [`LOGBOOK.md`](./LOGBOOK.md).
  2. Actualiza la tabla maestra de Goals.

---

## 4. Estándares Técnicos del Proyecto

- **Gestor de paquetes**: `uv` exclusivamente (usar `uv add`, `uv run python`, `uv run pytest`).
- **ORM & Modelos**: `SQLModel` para todas las entidades de base de datos. Asegurarse de importar los modelos antes de `SQLModel.metadata.create_all()`.
- **Estructura de CV**: El currículum se basa en la plantilla de [resume.md](./data/examples/Backend%20Engineer/resume.md) para [resume.lol](https://resume.lol). La experiencia laboral se organiza en **Iniciativas Técnicas (`WorkProject`)** bajo cada empresa, no en viñetas genéricas.
- **Testing**: Todo cambio en base de datos o agentes debe acompañarse de pruebas con `pytest` en `tests/`.
