# Matriz de atributos de calidad vs. estilo Hexagonal

> Sección del documento técnico · Responsable: Santiago (Dev C) · Jira SCRUM-37
> Atributos tomados del modelo de calidad de producto **ISO/IEC 25010**, más escalabilidad y observabilidad, que son relevantes para el stack.

**Escala:** ✅✅ lo soporta fuertemente · ✅ lo favorece · ➖ neutral (depende del stack, no del estilo) · ⚠️ lo limita o tiene un costo

---

## Matriz resumen

| Atributo de calidad | Impacto | Cómo lo soporta o limita Hexagonal | Evidencia en el proyecto |
|---|---|---|---|
| **Testabilidad** | ✅✅ | El dominio y los casos de uso dependen de **puertos** (interfaces), no de Mongo ni de FastAPI. Se prueban con adaptadores *in-memory* o mocks, sin levantar base de datos ni servidor. | Adaptador in-memory del backend (SCRUM-11) y pruebas unitarias del dominio mockeando puertos (SCRUM-15). En el frontend, `mockAdapter.js` permite probar todas las pantallas sin backend. |
| **Modificabilidad** | ✅✅ | Un cambio de infraestructura queda encerrado en un adaptador. El núcleo no se toca. | Cambiar de Mongo a otra BD = escribir otro adaptador que implemente `AnimalRepository` / `PostulacionRepository`. Pasar de mock a API real en la SPA = cambiar `VITE_USE_MOCK`, sin tocar vistas. |
| **Modularidad** | ✅✅ | Frontera explícita entre núcleo (dominio + casos de uso + puertos) y periferia (adaptadores). Cada pieza tiene una sola razón para cambiar. | Estructura propuesta del backend: `domain/`, `application/`, `ports/`, `adapters/in/`, `adapters/out/` *(confirmar con la estructura final de Gustavo)*. Los tres desarrolladores trabajaron en paralelo sobre esa frontera. |
| **Analizabilidad** | ✅ | Las reglas de negocio viven en un solo lugar y no se mezclan con código de HTTP o de BD. Encontrar "¿dónde se cierra una postulación?" es inmediato. | Regla de auto-cierre concentrada en `AprobarPostulacionUseCase` + métodos del dominio (`postulacion.aprobar()`, `animal.marcar_adoptado()`). |
| **Reusabilidad** | ✅ | Los casos de uso son reutilizables por cualquier adaptador de entrada (REST, CLI, tareas programadas, GraphQL). | El mismo `PostularUseCase` podría ser invocado por un script de carga masiva sin duplicar validaciones. |
| **Adaptabilidad / Portabilidad** | ✅✅ | La tecnología es un detalle reemplazable: el núcleo es Python puro, sin imports de FastAPI ni Motor. | Todo corre en contenedores Docker; el núcleo se puede portar a otro framework web (Flask, Litestar) cambiando solo el adaptador de entrada. |
| **Interoperabilidad** | ✅ | Se pueden añadir varios adaptadores de entrada o salida en paralelo para hablar con otros sistemas. | Hoy: REST / JSON:API. Añadir un adaptador de eventos o de notificaciones por correo no afecta al dominio. |
| **Fiabilidad (corrección de reglas)** | ✅ | Las invariantes se validan en el dominio, no en el controlador ni en el frontend, así que **ningún** canal de entrada puede saltárselas. | "No postular a un animal adoptado", "no duplicar postulación pendiente" y "auto-cierre" se validan en el núcleo; la API devuelve 409 con `code` claro y la SPA lo muestra. |
| **Seguridad** | ➖ / ✅ | El estilo no aporta autenticación por sí mismo, pero facilita aplicarla en el adaptador de entrada sin contaminar el dominio, y reduce la superficie: el dominio no expone detalles de la BD. | Fuera del alcance del taller (sin login). Si se agrega, iría como dependencia de FastAPI en el adaptador REST (JWT/OAuth2). |
| **Eficiencia de desempeño** | ⚠️ | Las capas de indirección (DTO → entidad → documento) agregan mapeos y copias. Cuesta más usar optimizaciones específicas del motor (agregaciones de Mongo) sin "filtrar" detalles al núcleo. | Impacto despreciable a la escala del proyecto. Propuesta: que el adaptador Mongo cierre las postulaciones restantes con un `updateMany`, así la optimización queda en la periferia y no en el dominio *(confirmar con Tomás)*. |
| **Escalabilidad** | ➖ | Hexagonal organiza el **interior** de un servicio; no define cómo se distribuye. La escalabilidad la dan el stack (Uvicorn async, réplicas de Mongo, contenedores). Sí facilita partir el sistema después, porque los límites ya están trazados. | Backend *stateless* en su propio contenedor → se puede replicar detrás de Nginx. |
| **Disponibilidad** | ➖ | No depende del estilo. La aporta la infraestructura. | Diseño de despliegue: `healthcheck` del backend y `depends_on: condition: service_healthy` en docker-compose *(confirmar con el compose final de Tomás)*. |
| **Observabilidad** | ✅ | Logging y métricas se pueden añadir como **decoradores de puertos** o *middleware* en adaptadores, sin tocar reglas de negocio. | Endpoint `GET /health` previsto en el diseño de despliegue. Logging estructurado posible en el adaptador de entrada. |
| **Usabilidad** | ➖ | No depende del estilo. Indirectamente ayuda: errores de dominio con código semántico producen mensajes claros en la UI. | `errors[].code` y `source.pointer` → la SPA marca el campo exacto que falló y explica "Luna ya fue adoptada". |
| **Simplicidad / curva de aprendizaje** | ⚠️ | Más archivos, interfaces y mapeos que un CRUD en capas. En sistemas pequeños puede ser **overengineering**. | Riesgo reconocido: el dominio es pequeño (4 entidades). Se justifica por la regla de auto-cierre y por el valor didáctico, no por el tamaño. |
| **Productividad inicial** | ⚠️ | Hay que definir puertos y contratos **antes** de implementar. Si el contrato cambia, bloquea a varios. | Dependencia crítica del plan: Dev A debía entregar los puertos antes que B y C. Mitigado con el contrato JSON:API cerrado primero (SCRUM-41) y mocks en ambos lados. |

---

## Lectura de la matriz

**Dónde gana Hexagonal:** mantenibilidad en todas sus subcaracterísticas (testabilidad, modificabilidad, modularidad, analizabilidad, reusabilidad) y adaptabilidad. Es un estilo pensado para que **la lógica de negocio sobreviva a los cambios de tecnología**.

**Dónde es neutral:** escalabilidad, disponibilidad, seguridad y usabilidad dependen del stack y de la infraestructura, no de la forma interna del código. Afirmar que Hexagonal "hace el sistema escalable" es un error común.

**Dónde cuesta:** desempeño (poco en la práctica), simplicidad y productividad inicial. El costo se paga al principio (diseñar puertos, escribir mapeos) y se recupera cuando el sistema cambia o crece.

**Conclusión para el caso:** en una plataforma de adopción con reglas de estado no triviales (postulación única activa, auto-cierre al aprobar), priorizar **corrección y testabilidad de las reglas** sobre rendimiento bruto es la decisión correcta. Hexagonal lo permite sin sacrificar ningún atributo crítico para este dominio.

---

## Fuentes
- ISO/IEC 25010:2023 — *Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*.
- Cockburn, A. (2005). *Hexagonal Architecture (Ports and Adapters)*. https://alistair.cockburn.us/hexagonal-architecture/
- Bass, L., Clements, P., Kazman, R. (2021). *Software Architecture in Practice*, 4.ª ed. Addison-Wesley (capítulos de atributos de calidad y tácticas).
- Richards, M., Ford, N. (2020). *Fundamentals of Software Architecture*. O'Reilly (características arquitectónicas y compromisos).
