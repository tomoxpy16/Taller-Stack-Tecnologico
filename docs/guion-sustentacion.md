# Guion de sustentación: diagramas, demo en vivo y plan B

Sistema de adopción de mascotas · Hexagonal · Vue + FastAPI + MongoDB + JSON:API + Docker

Duración objetivo: **12–15 min** (diagramas 5, demo 5, preguntas el resto).

---

## 1. Explicación de los diagramas (≈ 5 min)

Recorrer de lo general a lo particular. Una idea por diagrama.

| # | Diagrama | Qué decir (una frase clave) | Señalar |
|---|---|---|---|
| 1 | Alto nivel (`01-hld.png`) | "Todo corre en Docker Compose: la SPA en Vue habla con FastAPI por REST/JSON:API y el backend persiste en MongoDB." | Las tres zonas del backend: adaptador de entrada, núcleo, adaptadores de salida. |
| 2 | Contexto C4 (`02-c4-contexto.png`) | "Dos actores: el adoptante postula, el refugio publica y decide." | Que el sistema es una sola caja: no hay sistemas externos. |
| 3 | Contenedores C4 (`03-c4-contenedores.png`) | "Tres contenedores: Nginx sirve la SPA y reenvía `/api` al backend; el backend es el único que toca Mongo." | El proxy `/api` → evita CORS en producción. |
| 4 | Dinámico (`04-dinamico.png`) | "Así viaja una aprobación: PATCH → caso de uso → se aprueba una, se cierran las demás, el animal pasa a adoptado, todo en una operación." | La regla de cierre automático (ADR-010). |
| 5 | Despliegue (`05-despliegue.png`) | "Un solo `docker compose up`, con reinicio automático y volumen para los datos." | `restart` (ADR-005) y el volumen de Mongo. |
| 6 | Componentes C4 (`06-c4-componentes.png`) | "Aquí se ve el hexágono en el código: los routers son adaptadores de entrada, `dependencies.py` es la raíz de composición, el núcleo depende solo de puertos." | Puertos como `typing.Protocol`; adaptador Mongo y en memoria implementan el mismo puerto. |
| 7 | Modelo de datos (`07-modelo-datos.png`) | "Cuatro colecciones; el animal embebe salud, fotos y detalles por especie (ADR-002); las relaciones entre agregados son por id." | `motivo_rechazo`: distingue rechazo manual del cierre automático. |

**Cierre de la sección (frase puente a la demo):** "El frontend aplica la misma idea: un puerto de API con dos adaptadores, real y simulado. Por eso pudimos construirlo antes que el backend. Veámoslo funcionando."

---

## 2. Demo en vivo (≈ 5 min)

### Preparación (antes de entrar al salón)

1. Abrir VS Code en `Taller-Stack-Tecnologico`.
2. **Opción A, Docker (principal):** `docker compose up --build` y verificar `http://localhost` (frontend) y `http://localhost/api/v1/animals`.
   - ⚠️ Solo funciona completa si el backend en Docker ya usa el adaptador de MongoDB **con datos semilla**. Con el adaptador en memoria arranca vacío (sin refugios ni animales) y no hay endpoint para crear refugios.
3. **Opción B, sin Docker (respaldo probado):** `Terminal → Run Task… → "Demo completa (backend real + frontend)"`. Levanta el backend real de Gustavo con datos semilla y el frontend en `http://localhost:5174`.
4. Dejar abiertas dos pestañas: la app y Swagger (`http://localhost:8000/docs` en la Opción B).

Datos semilla de la demo: refugios *Huellitas Bogotá* y *Patitas Felices*; animales Luna, Michi, Kiwi, Toby, Nala (adoptada) y Coco; adoptantes Ana, Carlos y Laura. **Luna tiene 3 postulaciones pendientes**: es la que muestra el cierre automático.

### Recorrido

| Paso | Rol | Acción | Qué decir |
|---|---|---|---|
| 1 | Adoptante | Abrir el catálogo, filtrar por especie. | "Filtros y paginación salen del estándar JSON:API (`filter[especie]`)." |
| 2 | Adoptante | Abrir la ficha de **Kiwi** (ave). | "La ficha cambia según la especie: son los `detallesEspecie` embebidos del ADR-002." |
| 3 | Adoptante | Postular a Kiwi con el formulario vacío y luego completo. | "Primero valida el borde (formato); la regla de negocio la valida el dominio." |
| 4 | Adoptante | Intentar postular **otra vez** a Kiwi. | "El dominio lanza `PostulacionDuplicada`; el adaptador REST la traduce a 409 con el formato de error JSON:API y la UI muestra el mensaje." |
| 5 | Refugio | Cambiar a *Huellitas Bogotá* → panel → **Luna** (3 pendientes). | "Tres personas quieren a Luna." |
| 6 | Refugio | Aprobar la postulación de Ana → confirmar. | "Una sola operación: Ana aprobada, Carlos y Laura rechazadas por **cierre automático**, Luna pasa a adoptada, sin recargar la página (ADR-004)." |
| 7 | Adoptante | Volver al catálogo: Luna ya no está disponible. | "El estado es consistente en todo el sistema." |
| 8 | (opcional) | Swagger: `GET /v1/animals?include=refugio`. | "Documento compuesto: ficha y refugio en una sola petición." |

Si sobra tiempo: publicar un animal nuevo desde el panel del refugio.

---

## 3. Plan B (si la demo falla)

| Falla | Qué hacer |
|---|---|
| Docker no levanta o el backend arranca vacío | Pasar a la Opción B (tarea "Demo completa"). Tarda < 1 min. |
| La tarea de VS Code falla | `cd frontend && npm run dev:mock`: el frontend corre con el adaptador simulado, que respeta las mismas reglas. Decirlo explícitamente: "Esto es el adaptador simulado, la prueba de que el puerto funciona." |
| No hay computador o red | Mostrar las capturas en orden (abajo). |

Capturas en `docs/capturas/`, en el orden de la demo:

1. `01-catalogo.png`: catálogo con filtros.
2. `02-ficha.png`: ficha de un animal.
3. `03a-validacion.png`: validación del formulario.
4. `03b-error-duplicada.png`: 409 por postulación duplicada.
5. `04-mis-postulaciones.png`: estado de las postulaciones del adoptante.
6. `05-panel-antes.png`: panel del refugio con 3 pendientes sobre Luna.
7. `06-confirmar-aprobacion.png`: confirmación de la aprobación.
8. `07-panel-cierre-automatico.png`: resultado con "Rechazada · cierre automático".

---

## 4. Preguntas probables

- **¿Por qué Hexagonal y no MVC?** La regla de cierre automático es no trivial; aislarla permite probarla sin base de datos y cambiar Mongo o FastAPI sin tocarla.
- **¿Dónde vive la regla de cierre automático?** Solo en el caso de uso `AprobarPostulacion` del dominio; ni el router ni Mongo la conocen, y está cubierta por pruebas unitarias con el adaptador en memoria.
- **¿Por qué JSON:API y no JSON propio?** Contrato estándar para cualquier cliente futuro (ADR-003); errores con `source.pointer` que la UI muestra en el campo exacto.
- **¿Qué costo tiene el estilo?** Más archivos y más indirección; en un CRUD simple no se justificaría.
