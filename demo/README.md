# Demo local sin Docker (backend real + datos semilla)

Levanta el backend de FastAPI con los **repositorios en memoria** y datos de demostración, y el frontend en Vue apuntando a él. Sirve para la sustentación mientras el adaptador de MongoDB (SCRUM-21/23) y el seed en Docker no estén listos, y como plan B si Docker falla.

> Requiere el backend de `feature/casos-de-uso-in-memory` (endpoints de animales, postulaciones, refugios y adoptantes). Si esa rama aún no está unida, copia su carpeta `backend/` antes de correr la demo.

## Arrancar

Desde la raíz del repo:

```bash
# 1. Backend (puerto 8000)
cd backend
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn motor pydantic pydantic-settings
.venv/bin/python ../demo/run_demo.py

# 2. Frontend (en otra terminal, puerto 5174)
cd frontend
npm install
npx vite --port 5174 --open
```

- App: http://localhost:5174 (Vite reenvía `/api` al backend).
- Swagger: http://localhost:8000/docs

`run_demo.py` reemplaza el `lifespan` de la app para no conectarse a MongoDB y carga los datos semilla directamente en los repositorios en memoria. Los datos se pierden al reiniciar el backend, lo cual es útil para repetir la demo desde cero.

## Datos semilla

| Tipo | Datos |
|---|---|
| Refugios | r1 Huellitas Bogotá, r2 Patitas Felices |
| Animales | Luna (postulado), Michi (postulado), Kiwi, Toby, Coco (disponibles), Nala (adoptada) |
| Adoptantes | Ana Gómez, Carlos Ruiz, Laura Pérez |
| Postulaciones | **3 pendientes sobre Luna** (para mostrar el cierre automático), 1 sobre Michi, 1 aprobada sobre Nala |

## Prueba de extremo a extremo

Con la demo corriendo:

```bash
cd demo/e2e
npm install
npx playwright install chromium
node flujo-completo.mjs
```

Recorre catálogo → postular → postulación duplicada (409) → panel del refugio → aprobar (las demás quedan rechazadas por cierre automático) → publicar animal, y guarda capturas en `demo/e2e/capturas/`. Las capturas de la última ejecución están en `docs/evidencias/integracion-backend-real/`.
