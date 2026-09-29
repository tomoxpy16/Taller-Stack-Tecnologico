# Contrato API — Adopción de Mascotas (propuesta v0.1)

> Propuesta de Dev C para cerrar **SCRUM-41** con Gustavo (Dev A). El frontend ya está construido contra esta forma usando datos mock; si algo cambia, basta con ajustar `src/api/` en el frontend.

- **Base URL (vista desde el navegador):** `/api/v1`
  - ⚠️ El `nginx.conf` del repo **quita el prefijo `/api`** antes de pasar al backend. Por eso **los routers de FastAPI deben montarse en `/v1`** (ej. `app.include_router(animals_router, prefix="/v1")`). El proxy de Vite en desarrollo hace lo mismo.
- **Formato:** [JSON:API 1.1](https://jsonapi.org/format/)
- **Content-Type (request y response):** `application/vnd.api+json`
- **IDs:** strings (ObjectId de MongoDB serializado)
- **Sin autenticación** en el alcance del taller. El "rol" (refugio / adoptante) se elige en el frontend.

---

## 1. Recursos

### `refugios`
| Atributo | Tipo | Notas |
|---|---|---|
| `nombre` | string | requerido |
| `ciudad` | string | requerido |
| `telefono` | string | opcional |
| `email` | string | requerido, formato email |

Relaciones: `animals` (to-many).

### `animals`
| Atributo | Tipo | Notas |
|---|---|---|
| `nombre` | string | requerido, 1–60 caracteres |
| `especie` | enum | `perro` · `gato` · `ave` · `otro` |
| `edadMeses` | int | ≥ 0 |
| `sexo` | enum | `macho` · `hembra` |
| `temperamento` | string[] | ej. `["juguetón","sociable"]` |
| `salud` | object | `{ vacunado: bool, esterilizado: bool, notas: string }` |
| `fotos` | string[] | URLs |
| `detallesEspecie` | object | campos libres según especie (ej. perro: `tamano`, ave: `puedeHablar`) — **aquí se aprovecha el modelo documental de Mongo** |
| `estado` | enum | `disponible` · `postulado` · `adoptado` — **solo lectura**, lo cambia el dominio |
| `publicadoEn` | datetime ISO-8601 | solo lectura |

Relaciones: `refugio` (to-one), `postulaciones` (to-many).

### `adoptantes`
| Atributo | Tipo | Notas |
|---|---|---|
| `nombre` | string | requerido |
| `email` | string | requerido, único |
| `telefono` | string | requerido |
| `ciudad` | string | requerido |

### `postulaciones`
| Atributo | Tipo | Notas |
|---|---|---|
| `mensaje` | string | requerido, 10–500 caracteres (por qué quiere adoptar) |
| `estado` | enum | `pendiente` · `aprobada` · `rechazada` |
| `motivoCierre` | string \| null | `"rechazada_por_refugio"` o `"cierre_automatico"` — permite mostrar en UI por qué se cerró |
| `creadaEn` | datetime | solo lectura |
| `resueltaEn` | datetime \| null | solo lectura |

Relaciones: `animal` (to-one), `adoptante` (to-one).

---

### Nota sobre nombres (Mongo ↔ API)
La semilla de Tomás guarda en Mongo con **snake_case** (`edad_meses`, `detalles_especie`, `fecha_publicacion`, colección `animales`) y fotos como `{ url, descripcion }`. Lo ideal es que el **adaptador de salida** traduzca a los nombres del contrato, así el dominio y la API no dependen de cómo guarda Mongo. De todas formas **el frontend acepta ambas formas** (snake_case o camelCase, `type: "animals"` o `"animales"`, fotos como URL u objeto, `motivo_rechazo` o `motivoCierre`), así que no bloquea a nadie.

---

## 2. Endpoints

| Método | Ruta | Uso | Pantalla |
|---|---|---|---|
| GET | `/refugios` | Listar refugios | Selector de rol |
| GET | `/refugios/{id}` | Detalle | — |
| GET | `/animals` | Listado con filtros y paginación | Catálogo |
| GET | `/animals/{id}?include=refugio` | Ficha | Ficha del animal |
| POST | `/animals` | Refugio publica animal | Panel refugio |
| POST | `/adoptantes` | Registro simple de adoptante | Formulario postulación |
| GET | `/adoptantes/{id}` | Detalle | — |
| POST | `/postulaciones` | Adoptante postula | Formulario postulación |
| GET | `/postulaciones?filter[refugio]={id}&include=animal,adoptante` | Postulaciones del refugio | Panel refugio |
| GET | `/postulaciones?filter[adoptante]={id}&include=animal` | "Mis postulaciones" | Seguimiento |
| PATCH | `/postulaciones/{id}` | Aprobar / rechazar (`estado`) | Panel refugio |

### Parámetros de `GET /animals`
- `filter[estado]=disponible`
- `filter[especie]=perro`
- `filter[refugio]={id}`
- `page[number]=1&page[size]=12` (tamaño por defecto 12, máximo 50)
- `include=refugio`

La respuesta trae `meta.total` y `links.first/prev/next/last`.

---

## 3. Ejemplos

### Postular — `POST /postulaciones`
```json
{
  "data": {
    "type": "postulaciones",
    "attributes": { "mensaje": "Tengo patio grande y experiencia con perros." },
    "relationships": {
      "animal":    { "data": { "type": "animals",    "id": "66f1a0c2e4b0a1" } },
      "adoptante": { "data": { "type": "adoptantes", "id": "66f1a0c2e4b0z9" } }
    }
  }
}
```
**201 Created**
```json
{
  "data": {
    "type": "postulaciones",
    "id": "66f1b3d9aa01",
    "attributes": { "mensaje": "Tengo patio…", "estado": "pendiente", "motivoCierre": null,
                    "creadaEn": "2026-09-28T14:02:11Z", "resueltaEn": null },
    "relationships": {
      "animal":    { "data": { "type": "animals",    "id": "66f1a0c2e4b0a1" } },
      "adoptante": { "data": { "type": "adoptantes", "id": "66f1a0c2e4b0z9" } }
    }
  }
}
```

### Aprobar — `PATCH /postulaciones/{id}`
```json
{ "data": { "type": "postulaciones", "id": "66f1b3d9aa01", "attributes": { "estado": "aprobada" } } }
```
**200 OK** — devuelve la postulación aprobada e incluye en `included` el animal (ya `adoptado`) y las demás postulaciones que se cerraron automáticamente. Así el panel del refugio se actualiza con una sola respuesta:
```json
{
  "data": { "type": "postulaciones", "id": "66f1b3d9aa01", "attributes": { "estado": "aprobada", "...": "..." } },
  "included": [
    { "type": "animals", "id": "66f1a0c2e4b0a1", "attributes": { "estado": "adoptado", "...": "..." } },
    { "type": "postulaciones", "id": "66f1b3d9aa02", "attributes": { "estado": "rechazada", "motivoCierre": "cierre_automatico" } }
  ],
  "meta": { "postulacionesCerradasAutomaticamente": 1 }
}
```

---

## 4. Errores (formato JSON:API)

```json
{
  "errors": [{
    "status": "409",
    "code": "ANIMAL_NO_DISPONIBLE",
    "title": "El animal no está disponible",
    "detail": "Luna ya fue adoptada.",
    "source": { "pointer": "/data/relationships/animal" }
  }]
}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `SOLICITUD_MALFORMADA` | JSON inválido o `type` incorrecto |
| 404 | `RECURSO_NO_ENCONTRADO` | id inexistente |
| 409 | `ANIMAL_NO_DISPONIBLE` | postular a animal `adoptado` |
| 409 | `POSTULACION_DUPLICADA` | el adoptante ya tiene una `pendiente` sobre ese animal |
| 409 | `POSTULACION_YA_RESUELTA` | aprobar/rechazar una postulación que no está `pendiente` |
| 409 | `TRANSICION_INVALIDA` | cambio de estado del animal que su ciclo de vida no permite |
| 409 | `ID_NO_COINCIDE` | en un `PATCH`, `data.id` distinto del id de la URL |
| 405 | `METODO_NO_PERMITIDO` | verbo HTTP no soportado en esa ruta |
| 415 | `CONTENT_TYPE_INVALIDO` | falta `application/vnd.api+json` |
| 422 | `VALIDACION` | campo inválido; un error por campo con `source.pointer` (ej. `/data/attributes/mensaje`) |
| 500 | `ERROR_INTERNO` | no esperado (no expone detalles internos) |

Los errores de parámetros (`filter[...]`, `page[...]`, `include`) son 400 con `source.parameter` en vez de `source.pointer`.

**Implementación** (`backend/app/adapters/inbound/api/errors.py`): las excepciones de dominio (`app/domain/exceptions.py`) se traducen a estos códigos con un `exception_handler` de FastAPI; el dominio no conoce HTTP, solo el adaptador de entrada. Una subclase nueva hereda el código de su padre, y una regla sin mapeo responde 409 `REGLA_DE_NEGOCIO` (nunca 500).

### Las dos validaciones de la postulación

| Regla | Dónde se valida | Respuesta |
|---|---|---|
| No postular a un animal no disponible | `Animal.validar_postulable()` (dominio). Solo `adoptado` bloquea; `postulado` sigue aceptando (ver 5.1). | 409 `ANIMAL_NO_DISPONIBLE`, `detail`: "Luna ya fue adoptada." |
| No duplicar una postulación activa | Caso de uso `Postular`, con `PostulacionRepository.existe_pendiente()`. Solo cuenta la `pendiente`: tras un rechazo se puede volver a postular. | 409 `POSTULACION_DUPLICADA`, `detail`: "Ya tienes una postulación pendiente para Luna." |

La regla 1 se evalúa antes que la 2, y un rechazo no guarda nada ni cambia el estado del animal. En MongoDB, la regla 2 tiene además un respaldo en el índice único parcial `postulacion_pendiente_unica`, para el caso de dos peticiones simultáneas.

---

## 5. ⚠️ Decisiones que hay que cerrar (hay una inconsistencia en el PLAN.md)

1. **Estado `postulado` vs. regla "solo se puede postular a un animal `disponible`".**
   Si el animal pasa a `postulado` con la primera postulación y solo se admite postular a `disponible`, **nunca habría dos postulaciones pendientes** sobre el mismo animal y la regla de auto-cierre (la que justifica Hexagonal) nunca se ejecutaría.
   **Propuesta:** se puede postular mientras el animal esté en `disponible` **o** `postulado`; solo `adoptado` lo bloquea. `postulado` significa "tiene al menos una postulación pendiente".
2. **¿Qué pasa si el refugio rechaza todas las pendientes?** Propuesta: el animal vuelve a `disponible`.
3. **Registro de adoptante:** propuesta de registro mínimo en el mismo formulario de postulación (sin login). Si el email ya existe, se reutiliza el adoptante.
4. **Fotos:** URLs externas en el seed (sin subida de archivos) para no ampliar el alcance.
