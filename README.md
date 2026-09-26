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

1. No se puede postular a un animal que no esté `disponible`.
2. Un adoptante no puede tener más de una postulación `pendiente` sobre el mismo animal.
3. Al aprobar una postulación, el animal pasa a `adoptado` y todas las demás postulaciones `pendientes` sobre ese animal se rechazan automáticamente.

### Flujo principal (end-to-end)

1. El refugio publica un animal (`disponible`).
2. El adoptante consulta la ficha del animal y postula.
3. El sistema valida que el animal esté disponible y que no exista una postulación duplicada.
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
| Integración | REST / JSON:API | — | Contrato estándar para los recursos `animals`, `postulaciones` y `refugios`. |
| Contenedores | Docker + Docker Compose | Compose v2 | Levanta los 3 servicios (`mongodb`, `backend`, `frontend`) con un solo comando. |
| Pruebas | pytest + pytest-asyncio | pytest 8.3 | Pruebas unitarias del dominio y de integración contra MongoDB real. |

## Estructura del repositorio

```
.
├── docker-compose.yml         # 3 servicios: mongodb, backend, frontend
├── .env.example               # Variables de entorno (copiar a .env)
├── mongo/init/                # Datos semilla de Mongo (solo con volumen vacío)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # Arranque de FastAPI y registro de routers
│   │   ├── config.py          # Configuración por variables de entorno
│   │   ├── domain/            # Entidades y reglas de negocio (sin dependencias externas)
│   │   ├── application/
│   │   │   ├── ports/         # Puertos (Protocol): AnimalRepository, PostulacionRepository...
│   │   │   └── use_cases/     # Casos de uso: postular, aprobar, rechazar...
│   │   └── adapters/
│   │       ├── inbound/api/   # Adaptador de entrada: routers FastAPI (JSON:API)
│   │       └── outbound/persistence/
│   │           ├── mongo/     # Adaptador de salida real (MongoDB): cliente, índices, repositorios
│   │           └── memory/    # Adaptador in-memory para pruebas
│   └── tests/
│       ├── unit/              # Dominio y casos de uso con puertos mockeados
│       └── integration/       # Backend contra Mongo real
└── frontend/
    ├── Dockerfile             # Build de Vite (npm run build → dist/) + Nginx
    └── nginx.conf             # Sirve la SPA y redirige /api → backend
                               # (el proyecto Vue se agrega aquí)
```

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

> Mientras el proyecto Vue no esté en `frontend/`, el servicio `frontend` no compila. Para levantar solo la base de datos y la API: `docker compose up --build -d mongodb backend`.

### 4. Verificar el despliegue

```bash
docker compose ps                     # los servicios deben aparecer como "healthy"
curl http://localhost:8000/health     # {"status":"ok","mongodb":"up"}
```

### 5. Acceder al sistema

| Servicio | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend (API) | http://localhost:8000 |
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
- **Ver los logs de un servicio**: `docker compose logs -f backend` (o `mongodb`, `frontend`).

### Datos semilla e índices

- `mongo/init/01-seed.js` carga 2 refugios, 3 adoptantes, 6 animales (perros, gatos y un ave, con ficha de salud y fotos embebidas) y 4 postulaciones. Solo se ejecuta cuando el volumen de Mongo está vacío; para recargarla: `docker compose down -v && docker compose up -d`.
- La semilla deja listo el escenario de la demo: **Rocky** tiene 2 postulaciones pendientes (al aprobar una, la otra debe cerrarse automáticamente) y **Nala** ya está adoptada con su historial.
- Los índices los crea el backend en cada arranque (`backend/app/adapters/outbound/persistence/mongo/indexes.py`, operación idempotente). Incluyen un índice único parcial que impide dos postulaciones `pendiente` del mismo adoptante al mismo animal.

## Desarrollo local sin Docker

```bash
# Mongo en contenedor
docker compose up -d mongodb

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Pruebas: las de integración usan una base temporal en el Mongo local y se omiten si no está arriba
pytest                    # todas
pytest -m integration     # solo integración
pytest -m "not integration"

# Frontend: en desarrollo, configurar el proxy de Vite para que /api apunte a http://localhost:8000
# (quitando el prefijo /api), igual que hace Nginx en Docker.
```

## Estrategia de ramas

- `main`: versión estable y entregable. Solo recibe merges desde `develop`; de aquí salen el TAG y el Release.
- `develop`: rama de integración.
- `feature/<área>-<descripción>`: una rama por tarea, creada desde `develop` y fusionada con Pull Request. Ejemplos: `feature/backend-casos-uso`, `feature/mongo-adaptadores`, `feature/frontend-panel-refugio`.

Mensajes de commit sugeridos: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
