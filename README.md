# Plataforma de Adopción de Mascotas — Arquitectura Hexagonal

## Descripción del sistema

Plataforma web para gestionar la adopción de mascotas. Los refugios publican animales con su ficha (especie, edad, estado de salud, temperamento y fotos), los adoptantes postulan a un animal y el refugio aprueba o rechaza cada postulación, con seguimiento del estado del proceso.

### Entidades del dominio

| Entidad | Descripción | Estados |
|---|---|---|
| **Refugio** | Organización que publica animales disponibles. | — |
| **Animal** | Ficha con especie, edad, salud, temperamento y fotos. Los campos varían según la especie (perro, gato, ave). | `disponible`, `postulado`, `adoptado` |
| **Adoptante** | Persona que postula a un animal. | — |
| **Postulación** | Vincula un adoptante con un animal. | `pendiente`, `aprobada`, `rechazada` |

### Reglas de negocio

1. No se puede postular a un animal `adoptado`. Sí se puede postular a uno `postulado` (que ya tiene postulaciones pendientes); así puede haber varias pendientes y la regla 3 tiene sentido.
2. Un adoptante no puede tener más de una postulación `pendiente` sobre el mismo animal.
3. Al aprobar una postulación, el animal pasa a `adoptado` y todas las demás postulaciones `pendientes` sobre ese animal se rechazan automáticamente.

### Flujo principal (end-to-end)

1. El refugio publica un animal (`disponible`).
2. El adoptante consulta la ficha del animal y postula.
3. El sistema valida que el animal no esté adoptado y que no exista una postulación duplicada. La primera postulación pasa el animal a `postulado`.
4. El refugio revisa la postulación y la aprueba o la rechaza.
5. Si la aprueba, el animal pasa a `adoptado` y se cierran automáticamente las demás postulaciones pendientes sobre ese animal.

### Arquitectura

El sistema sigue el estilo **Hexagonal (Puertos y Adaptadores)**. Las reglas de negocio viven en el dominio y no dependen de la infraestructura: FastAPI es el adaptador de entrada y MongoDB el adaptador de salida, conectados al dominio a través de puertos. Así, cualquiera de ellos se puede sustituir (por ejemplo, por un adaptador en memoria para las pruebas) sin tocar las reglas.

## Tecnologías usadas

| Capa | Tecnología | Versión | Rol en el sistema |
|---|---|---|---|
| Estilo arquitectónico | Hexagonal (Puertos y Adaptadores) | — | Aísla las reglas de negocio de la infraestructura. |
| Frontend | Vue.js + Vite | Vue 3 | Interfaz para adoptantes y panel de aprobación del refugio. |
| Servidor web | Nginx | 1.27 | Sirve el frontend compilado y redirige `/api` al backend. |
| Backend | FastAPI + Uvicorn | FastAPI 0.115, Python 3.12 | Expone los casos de uso como API REST; `Depends()` inyecta los adaptadores. |
| Validación | Pydantic | 2.10 | Valida formato y tipos de las peticiones en el borde. |
| Persistencia | MongoDB + Motor (driver async) | MongoDB 7.0, Motor 3.6 | Almacena documentos con estructura variable por especie, con fotos y ficha de salud embebidas. |
| Integración | REST / JSON:API | JSON:API 1.1 | Contrato estándar para los recursos `animals`, `postulaciones`, `refugios` y `adoptantes`. |
| Contenedores | Docker + Docker Compose | Compose v2 | Levanta los 3 servicios (`mongodb`, `backend`, `frontend`) con un solo comando. |
| Pruebas | pytest + pytest-asyncio + httpx | pytest 8.3 | Pruebas unitarias del dominio, de la API y de integración contra MongoDB real. |

## Estructura del repositorio

```
.
├── docker-compose.yml         # 3 servicios: mongodb, backend, frontend
├── .env.example               # Variables de entorno (copiar a .env)
├── mongo/init/01-seed.js      # Datos semilla de Mongo (solo con volumen vacío)
├── docs/                      # Contrato API, diagramas, matrices, wireframes y sustentación
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt       # requirements-dev.txt agrega las herramientas de pruebas
│   ├── app/
│   │   ├── main.py            # Arranque de FastAPI: conexión a Mongo, índices y routers
│   │   ├── config.py          # Configuración por variables de entorno
│   │   ├── domain/            # entities.py y exceptions.py: entidades y reglas (sin dependencias externas)
│   │   ├── application/
│   │   │   ├── ports/         # Puertos (Protocol): AnimalRepository, PostulacionRepository...
│   │   │   └── use_cases/     # Casos de uso: postular, aprobar, rechazar, publicar...
│   │   └── adapters/
│   │       ├── inbound/api/   # Adaptador de entrada: routers FastAPI (JSON:API) y errores -> HTTP
│   │       │   └── dependencies.py  # Composition root: decide qué adaptador de salida se inyecta
│   │       └── outbound/persistence/
│   │           ├── mongo/     # Adaptador de salida real: cliente, índices y repositorios
│   │           └── memory/    # Adaptador in-memory (pruebas)
│   └── tests/
│       ├── unit/              # Dominio, casos de uso con mocks, API y reglas de arquitectura
│       └── integration/       # API completa (in-memory) y adaptador contra Mongo real
└── frontend/
    ├── Dockerfile             # Build de Vite (npm run build → dist/) + Nginx
    ├── nginx.conf             # Sirve la SPA y redirige /api → backend
    └── src/
        ├── api/               # Puerto hacia el backend + adaptador HTTP
        ├── views/             # Catálogo, ficha, postulación, mis postulaciones, panel del refugio
        └── components/
```

Flujo de una petición: `Vue (src/api)` → `Nginx /api/v1/...` → `FastAPI /v1/...` (router) → caso de uso → puerto → repositorio de Mongo → MongoDB.

**Regla de dependencias:** `domain` no importa nada de `application` ni de `adapters`; `application` solo depende de `domain`; los `adapters` dependen hacia adentro, nunca al revés.

## Pasos para despliegue

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o Docker Engine) con **Docker Compose v2**, en ejecución.
- Git.
- Puertos libres: `8080` (frontend), `8000` (backend) y `27017` (MongoDB). Se pueden cambiar en `.env`.

### 1. Clonar el repositorio

```bash
git clone https://github.com/tomoxpy16/Taller-Stack-Tecnologico.git
cd Taller-Stack-Tecnologico
```

### 2. Configurar las variables de entorno

```bash
cp .env.example .env        # Windows (PowerShell): Copy-Item .env.example .env
```

Los valores por defecto funcionan sin cambios. En `.env` se ajustan las credenciales de MongoDB, el nombre de la base de datos y los puertos publicados.

### 3. Construir y levantar los servicios

```bash
docker compose up --build -d
```

Docker Compose arranca los servicios en orden: primero `mongodb`; cuando pasa su healthcheck, `backend`; y cuando el backend responde, `frontend`. En el primer arranque, MongoDB carga los datos semilla automáticamente.

### 4. Verificar el despliegue

```bash
docker compose ps                               # mongodb y backend deben aparecer como "healthy"
curl http://localhost:8000/health               # {"status":"ok","mongodb":"up"}
curl http://localhost:8080/api/v1/refugios      # los 2 refugios de la semilla, pasando por Nginx
```

### 5. Acceder al sistema

| Servicio | URL |
|---|---|
| Frontend | http://localhost:8080 |
| API vía Nginx (como la usa el frontend) | http://localhost:8080/api/v1 |
| Backend (API directa) | http://localhost:8000/v1 |
| Documentación OpenAPI | http://localhost:8000/docs |
| Healthcheck | http://localhost:8000/health |
| MongoDB | mongodb://admin:admin123@localhost:27017/?authSource=admin |

### 6. Detener el sistema

```bash
docker compose down        # detiene y elimina los contenedores; conserva los datos
docker compose down -v     # además borra el volumen de MongoDB (la semilla se recarga en el próximo arranque)
```

### Solución de problemas

- **`error during connect ... dockerDesktopLinuxEngine`**: Docker Desktop no está abierto. Iniciarlo y esperar a que termine de arrancar.
- **`port is already allocated`**: otro programa usa el puerto. Cambiar `FRONTEND_PORT`, `BACKEND_PORT` o `MONGO_PORT` en `.env`.
- **El frontend muestra "Not Found" o la API responde 404**: los routers se montan en `/v1` porque Nginx quita el prefijo `/api`. Comprobar `curl http://localhost:8000/v1/refugios`; si responde 404, el contenedor del backend está desactualizado: `docker compose up -d --build backend`.
- **Los cambios en la semilla no aparecen**: la semilla solo se carga con el volumen vacío. Ver [Datos semilla e índices](#datos-semilla-e-índices).
- **Ver los logs de un servicio**: `docker compose logs -f backend` (o `mongodb`, `frontend`).

### Datos semilla e índices

- `mongo/init/01-seed.js` carga 2 refugios, 3 adoptantes, 6 animales (perros, gatos y un ave, con ficha de salud y fotos embebidas) y 4 postulaciones. Solo se ejecuta cuando el volumen de Mongo está vacío; para recargarla (⚠️ borra todo lo creado desde la aplicación): `docker compose down -v && docker compose up -d`.
- La semilla deja listo el escenario de la demo: **Rocky** tiene 2 postulaciones pendientes (al aprobar una desde el panel del refugio, la otra se cierra automáticamente y Rocky pasa a `adoptado`) y **Nala** ya está adoptada con su historial.
- Mongo guarda los campos en snake_case (`edad_meses`, colección `animales`); el adaptador de Mongo los traduce a las entidades del dominio y la API los expone en camelCase (`edadMeses`, tipo `animals`).
- Los índices los crea el backend en cada arranque (`backend/app/adapters/outbound/persistence/mongo/indexes.py`, operación idempotente). Incluyen un índice único parcial que impide dos postulaciones `pendiente` del mismo adoptante al mismo animal, y uno único por email de adoptante. Si dos peticiones simultáneas chocan con ellos, el adaptador responde 409 `POSTULACION_DUPLICADA` o reutiliza el adoptante existente, nunca 500.

## API

API REST con formato [JSON:API 1.1](https://jsonapi.org/format/) (`Content-Type: application/vnd.api+json`). El contrato completo, con ejemplos, reglas de negocio y códigos de error, está en [`docs/contrato-api-jsonapi.md`](docs/contrato-api-jsonapi.md); la documentación interactiva, en http://localhost:8000/docs.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/v1/refugios` · `/v1/refugios/{id}` | Listar refugios / detalle |
| GET | `/v1/animals` | Catálogo con `filter[estado\|especie\|refugio]`, `page[number]`, `page[size]` e `include=refugio` |
| GET | `/v1/animals/{id}` | Ficha del animal |
| POST | `/v1/animals` | El refugio publica un animal |
| POST | `/v1/adoptantes` · GET `/v1/adoptantes/{id}` | Registro del adoptante (si el email existe, se reutiliza) / detalle |
| POST | `/v1/postulaciones` | El adoptante postula |
| GET | `/v1/postulaciones?filter[refugio]=…` o `?filter[adoptante]=…` | Panel del refugio / "Mis postulaciones" |
| PATCH | `/v1/postulaciones/{id}` | Aprobar o rechazar (`estado`); al aprobar devuelve en `included` el animal y las postulaciones cerradas |

Las violaciones de reglas de negocio responden **409** con un `code` (`ANIMAL_NO_DISPONIBLE`, `POSTULACION_DUPLICADA`, `POSTULACION_YA_RESUELTA`...), y los datos inválidos, **422** con un error por campo.

## Pruebas

```bash
cd backend
pytest                        # todas (182)
pytest -m "not integration"   # sin Mongo: dominio, casos de uso, API sobre el adaptador in-memory y arquitectura (162)
pytest -m integration         # contra Mongo real: adaptador de Mongo, índices y flujo completo por la API (20)
pytest tests/unit --cov=app/domain --cov=app/application --cov-report=term-missing   # cobertura del núcleo
```

- Las pruebas marcadas `integration` necesitan Mongo arriba (`docker compose up -d mongodb`). Cada prueba crea una base temporal `adopciones_test_*` y la borra al terminar, así que no tocan los datos de la aplicación. Si Mongo no está disponible, se omiten en vez de fallar.
- `tests/unit/test_arquitectura.py` verifica la regla de dependencias de Hexagonal sobre los imports reales: si alguien hace que el dominio importe FastAPI o Motor, la prueba falla.
- `tests/integration/test_api_mongo.py` recorre el flujo principal completo (postular, duplicada, aprobar con cierre automático) y comprueba lo que quedó guardado en Mongo.

## Desarrollo local sin Docker

```bash
# Mongo en contenedor
docker compose up -d mongodb

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload    # API en http://localhost:8000/v1, usando el Mongo del contenedor

# Frontend (el proxy de Vite ya redirige /api → http://localhost:8000 quitando el prefijo, igual que Nginx)
cd frontend
npm install
npm run dev          # contra la API real en http://localhost:5173
```

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/contrato-api-jsonapi.md`](docs/contrato-api-jsonapi.md) | Contrato JSON:API v1.0, reglas de negocio y decisiones cerradas |
| [`docs/diagramas/`](docs/diagramas/) | HLD, C4 (contexto, contenedores, componentes), dinámico, despliegue y modelo de datos |
| [`docs/matriz-atributos-calidad.md`](docs/matriz-atributos-calidad.md) | Atributos de calidad vs. estilo Hexagonal |
| [`docs/matriz-principios.md`](docs/matriz-principios.md) | Principios de diseño (SOLID, STUPID...) vs. estilo |
| [`docs/patrones-antipatrones.md`](docs/patrones-antipatrones.md) | Patrones y antipatrones aplicados a Hexagonal |
| [`docs/revision-validaciones-errores.md`](docs/revision-validaciones-errores.md) | Revisión cruzada de validaciones y manejo de errores |
| [`docs/investigacion-vue-rest-jsonapi.md`](docs/investigacion-vue-rest-jsonapi.md) | Investigación de Vue + REST/JSON:API |
| [`docs/wireframes/`](docs/wireframes/) | Wireframes de las pantallas |
| [`docs/sustentacion/`](docs/sustentacion/) | Diapositivas y guion de la sustentación |

## Estrategia de ramas

- `main`: versión estable y entregable. Solo recibe merges desde `develop`; de aquí salen el TAG y el Release.
- `develop`: rama de integración.
- `feature/<área>-<descripción>`: una rama por tarea, creada desde `develop` y fusionada con Pull Request. Ejemplos: `feature/backend-casos-uso`, `feature/mongo-adaptadores`, `feature/frontend-panel-refugio`.

Mensajes de commit sugeridos: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
