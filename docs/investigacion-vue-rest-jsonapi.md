# Investigación del stack — Vue.js y REST / JSON:API

> Sección del documento técnico · Responsable: Santiago (Dev C) · Jira SCRUM-30
> Cubre, para cada tecnología, los 8 puntos que pide el taller. El punto "qué tan común es el stack completo" lo desarrolla Tomás en SCRUM-46; aquí solo se aportan los datos de Vue.

---

## 1. Vue.js

### 1.1 Definición clara
**Qué es:** un framework **progresivo** de JavaScript para construir interfaces de usuario basadas en componentes. "Progresivo" significa que se puede usar desde un solo widget dentro de una página existente hasta una SPA completa con router, estado y build tooling.

**Qué no es:**
- No es un framework full-stack ni un backend. No tiene acceso a base de datos ni lógica de servidor.
- No es un meta-framework de renderizado (eso es Nuxt). Vue por sí solo hace renderizado en cliente (CSR).
- No es una librería de componentes visuales (como Bootstrap o Vuetify). Vue da el modelo de componentes; el aspecto visual lo pone el equipo.
- No impone una arquitectura de aplicación: no obliga a capas, puertos ni un patrón de estado concreto.

### 1.2 Características principales
| Característica | Qué aporta |
|---|---|
| **Reactividad** basada en proxies (`ref`, `reactive`, `computed`) | La vista se actualiza sola cuando cambia el estado. En el proyecto: el panel del refugio refleja el auto-cierre sin recargar. |
| **Single-File Components** (`.vue`) | Plantilla, lógica y estilos de un componente en un mismo archivo, con estilos acotados (`scoped`). |
| **Composition API** (`<script setup>`) | Lógica reutilizable como funciones; mejor soporte de tipos que la Options API. |
| **Plantillas declarativas** compiladas | El compilador optimiza la plantilla (hoisting estático, patch flags) antes de llegar al Virtual DOM. |
| **Ecosistema oficial** | Vue Router (rutas), Pinia (estado global), Vite (build/dev server), Vue DevTools. |
| **Curva de aprendizaje suave** | HTML + JS estándar; no requiere JSX ni TypeScript. |

### 1.3 Historia y evolución
| Año | Hito |
|---|---|
| 2014 (feb.) | Evan You, ex-ingeniero de Google que trabajaba con AngularJS, publica Vue: "extraer lo que me gustaba de Angular y hacer algo muy ligero". |
| 2016 (30 sep.) | **Vue 2.0**: Virtual DOM, renderizado en servidor, adopción masiva (especialmente en China y en el ecosistema Laravel). |
| 2020 (18 sep.) | **Vue 3.0**: reescritura en TypeScript, reactividad con `Proxy`, **Composition API**, mejor tree-shaking. |
| 2020 → | Vite (del mismo autor) reemplaza a Webpack/Vue CLI como herramienta de build recomendada. Pinia reemplaza a Vuex como store oficial. |
| 2023 (31 dic.) | **Fin de soporte de Vue 2**. |
| 2024 (1 sep.) | **Vue 3.5**: optimizaciones de memoria y reactividad, props reactivas desestructurables. Es la rama estable actual (3.5.40, julio 2026). |
| 2026 | **Vue 3.6** en release candidate con **Vapor Mode** (compilación sin Virtual DOM, opcional por componente) y un nuevo núcleo reactivo basado en *alien-signals*. |

### 1.4 Ventajas y desventajas
| Ventajas | Desventajas |
|---|---|
| Curva de aprendizaje baja; productivo en horas, ideal para un taller con plazo corto. | Menor mercado laboral que React (≈17,6 % vs 44,7 % de uso en Stack Overflow 2025). |
| Reactividad automática: menos código para mantener la UI sincronizada con los datos. | Menos librerías de terceros que React, sobre todo en componentes empresariales. |
| Alta satisfacción de desarrolladores (84 % en State of JS 2025). | La migración Vue 2 → 3 fue costosa y dejó fragmentación en tutoriales y paquetes. |
| Bundle pequeño (en este proyecto: ≈ 43 kB gzip el JS principal). | Flexibilidad = decisiones: hay dos APIs (Options y Composition) y el equipo debe fijar convenciones. |
| Tooling oficial integrado (Vite, Router, Pinia, DevTools). | Sin SSR de fábrica: para SEO se necesita Nuxt, que agrega complejidad. |

### 1.5 Casos de uso — cuándo usarlo y cuándo no
**Usarlo cuando:**
- Se construye una SPA o un panel administrativo con mucho estado de UI que cambia (formularios, tableros, listas filtrables).
- El equipo es pequeño o tiene poca experiencia en frontend y necesita resultados rápidos.
- Se quiere modernizar por partes una aplicación existente (se puede montar Vue en una sola sección).

**No usarlo (o preferir otra cosa) cuando:**
- El sitio es mayormente contenido estático y el SEO es crítico → Nuxt, Astro o SSG.
- La organización necesita el mayor pool de contratación posible o un ecosistema empresarial muy específico → React o Angular.
- La app es móvil nativa → Flutter, React Native o nativo.

### 1.6 Casos de aplicación en la industria
- **GitLab:** Vue es el framework principal de su frontend; tiene guías oficiales de desarrollo con Vue en su documentación.
- **Adobe (Behance / Portfolio):** frontend modernizado con Vue.
- **Nintendo:** sitios regionales en Europa (Alemania, Francia, España, Reino Unido).
- **Xiaomi:** sitios web y aplicaciones de alto tráfico.
- **Laravel:** Vue viene integrado en el ecosistema (Inertia, starter kits), lo que lo volvió muy común en backends PHP.

### 1.7 Relación entre el estilo (Hexagonal) y Vue.js
Hexagonal es un estilo del **backend**: aísla el dominio de la infraestructura. En este sistema Vue ocupa el lugar de un **actor primario** que "conduce" la aplicación desde fuera del hexágono, a través del **adaptador de entrada REST**. Vue nunca conoce el dominio ni Mongo; solo conoce el contrato JSON:API.

Además, el frontend aplica la misma idea a pequeña escala:
- `src/api/index.js` es el **puerto** de la SPA hacia el backend. Las vistas solo importan `api` desde ahí.
- Detrás está el **adaptador HTTP** (`httpAdapter.js`), que traduce las llamadas a JSON:API contra la API de FastAPI.
- Durante el desarrollo hubo un segundo adaptador con datos en memoria que permitió construir las pantallas antes de que existiera el backend; se retiró al integrar para que la app solo muestre datos reales o el error.

Resultado práctico: cambiar de adaptador no tocó ninguna vista. Es la misma propiedad que Hexagonal promete para el dominio: **sustituir infraestructura sin reescribir la lógica que la usa**.

---

## 2. REST / JSON:API

> REST es el **estilo** de integración; JSON:API es la **especificación concreta** del formato de los mensajes sobre REST. Se presentan juntos porque en el proyecto funcionan como un solo protocolo de integración.

### 2.1 Definición clara
**REST** (Representational State Transfer): estilo arquitectónico para sistemas distribuidos definido por Roy Fielding en su tesis doctoral (2000). Se basa en **recursos** identificados por URIs, manipulados con los verbos estándar de HTTP, con comunicación sin estado entre cliente y servidor.

**JSON:API:** especificación que define **cómo** un cliente pide y modifica recursos y **cómo** responde el servidor en JSON: estructura de documentos (`data`, `attributes`, `relationships`, `included`, `errors`, `meta`, `links`), filtros, paginación, ordenamiento, inclusión de relacionados y formato de errores. Tiene media type propio registrado en IANA: `application/vnd.api+json`.

**Qué no es:**
- REST no es "cualquier API que use JSON sobre HTTP". Una API RPC con URLs tipo `/aprobarPostulacion` no es REST.
- JSON:API no es un protocolo de transporte ni un reemplazo de HTTP. Tampoco es GraphQL: el cliente no define la forma arbitraria de la respuesta, solo elige qué relaciones incluir y qué campos traer (*sparse fieldsets*).
- JSON:API no es OpenAPI/Swagger: OpenAPI *describe* una API; JSON:API *estandariza el formato* de sus mensajes. Se complementan (FastAPI genera OpenAPI automáticamente).

### 2.2 Características principales
**REST:**
- Recursos con URI propia (`/animals/{id}`).
- Interfaz uniforme: `GET` lee, `POST` crea, `PATCH` modifica parcialmente, `DELETE` elimina.
- Sin estado: cada petición lleva toda la información necesaria.
- Códigos de estado HTTP con significado (`201 Created`, `404`, `409 Conflict`, `422`).
- Cacheable y en capas (proxies como Nginx pueden intermediar).

**JSON:API (lo que usamos):**
| Característica | En el proyecto |
|---|---|
| Documento con `data` / `attributes` / `relationships` | Una postulación referencia su `animal` y su `adoptante` por relación, no por campos sueltos. |
| **Compound documents** (`include` → `included`) | `GET /animals/{id}?include=refugio` trae la ficha y su refugio en una sola petición. Al aprobar, la respuesta incluye el animal adoptado y las postulaciones cerradas automáticamente. |
| Filtros y paginación estandarizados | `filter[estado]=disponible`, `page[number]` / `page[size]`, `links.next`. |
| **Objeto de error estándar** | `errors[]` con `status`, `code`, `detail` y `source.pointer` → la UI marca el campo exacto que falló. |
| Negociación por media type | `Content-Type: application/vnd.api+json` (415 si falta). |

### 2.3 Historia y evolución
| Año | Hito |
|---|---|
| 2000 | Roy Fielding define REST en su tesis doctoral (UC Irvine). Fielding también fue coautor de la especificación HTTP/1.1. |
| 2000–2010 | REST reemplaza progresivamente a SOAP/XML en APIs web públicas. |
| 2013 (may.) | Yehuda Katz (co-creador de Ember.js) redacta JSON:API a partir de lo aprendido con Ember Data. |
| 2013 (21 jul.) | Registro del media type `application/vnd.api+json` en IANA. |
| 2015 (29 may.) | **JSON:API 1.0** final. |
| 2019 | JSON:API entra al **núcleo de Drupal** (8.7) como módulo estable. |
| 2022 (30 sep.) | **JSON:API 1.1** final: extensiones y perfiles, identificadores locales (`lid`) para crear recursos relacionados en una sola petición, miembros `@`. |
| 2026 | 1.1 es la versión vigente; 1.2 está en desarrollo. |

### 2.4 Ventajas y desventajas
| Ventajas | Desventajas |
|---|---|
| REST es el estándar de facto: cualquier cliente, herramienta o proxy lo entiende. | JSON:API es **verboso**: una respuesta simple tiene más anidación que un JSON "plano". |
| JSON:API elimina el *bikeshedding* sobre el formato: el equipo no discute cómo paginar ni cómo devolver errores. | Menos popular que el REST "libre"; FastAPI **no lo trae de fábrica**, hay que serializar a mano o con una librería. |
| `include` reduce viajes de red (evita el problema N+1 del cliente). | Operaciones que no son CRUD (aprobar una postulación) se modelan como cambio de estado vía `PATCH`, lo cual es menos explícito que un endpoint de acción. |
| Errores con `source.pointer` → validaciones fáciles de mostrar en la UI. | Sobre-fetching o under-fetching sigue existiendo frente a GraphQL en pantallas muy compuestas. |
| Cacheable con HTTP estándar, fácil de probar con curl o Postman. | Ecosistema de librerías cliente más pequeño que el de REST simple o GraphQL. |

### 2.5 Casos de uso — cuándo usarlo y cuándo no
**Usar REST + JSON:API cuando:**
- El dominio se modela naturalmente como **recursos con relaciones** (animales, refugios, postulaciones).
- Varios equipos o clientes consumen la API y conviene un contrato uniforme sin documentar convenciones propias.
- Se necesita paginación, filtros y errores consistentes desde el día uno.

**No usarlo cuando:**
- El cliente necesita consultas muy flexibles y heterogéneas por pantalla → **GraphQL**.
- Comunicación interna entre microservicios con alto rendimiento → **gRPC**.
- Se requieren actualizaciones en tiempo real servidor → cliente → **WebSockets** o **SSE**.
- API mínima de 2 o 3 endpoints donde la verbosidad de JSON:API no se justifica → REST simple.

### 2.6 Casos de aplicación en la industria
- **Drupal:** expone todo su contenido vía JSON:API desde el núcleo (Drupal 8.7, 2019), base de muchos proyectos *headless* gubernamentales y de medios.
- **Ember Data:** usa JSON:API como formato por defecto; la especificación nació de ahí.
- **REST en general:** APIs públicas de GitHub (v3), Stripe y Twilio son referentes de diseño REST por recursos.

### 2.7 Relación entre el estilo (Hexagonal) y REST / JSON:API
En Hexagonal, REST es exactamente un **adaptador de entrada (driving adapter)**:
- El router de FastAPI traduce una petición JSON:API a una llamada a un **caso de uso** (`PostularUseCase`, `AprobarPostulacionUseCase`) y traduce la respuesta del caso de uso de vuelta a JSON:API.
- El dominio **no sabe que existe HTTP**. Las reglas lanzan excepciones de dominio (`AnimalNoDisponible`, `PostulacionDuplicada`, `PostulacionYaResuelta`), y solo el adaptador REST las mapea a `409` con `code` y `detail` en el formato de JSON:API.
- Si mañana se quisiera exponer los mismos casos de uso por GraphQL o por CLI, se agrega **otro adaptador de entrada** sin tocar el dominio. Esta es la justificación central del estilo.
- JSON:API refuerza el **contrato** entre el adaptador y sus consumidores. Por eso el contrato (`contrato-api-jsonapi.md`) se cerró antes de implementar (SCRUM-41).

---

## Fuentes
- Vue.js — Wikipedia (fechas de versiones, fin de soporte de Vue 2, versión estable): https://en.wikipedia.org/wiki/Vue.js
- Vue School, *Vue.js 2025 in review and a peek into 2026*: https://vueschool.io/articles/news/vue-js-2025-in-review-and-a-peek-into-2026/
- RepoJournal, *Vue 3.6 RC lands with Vapor Mode complete* (jul. 2026): https://repojournal.com/showcase/vuejs/2026-07-18
- Encuesta Stack Overflow 2025 y State of JS 2025 (recopilación): https://gist.github.com/tkrotoff/b1caa4c3a185629299ec234d2314e190
- GitLab — Frontend Development Guidelines: https://docs.gitlab.com/development/fe_guide
- Monterail, *Top companies using Vue.js in 2026*: https://www.monterail.com/blog/top-companies-using-vue-js
- JSON:API — About / update history: https://jsonapi.org/about/
- JSON:API — Especificación v1.1: https://jsonapi.org/format/1.1/
- Drupal, *JSON:API lands in Drupal core*: https://www.drupal.org/blog/jsonapi-lands-in-drupal-core
- Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures*. Tesis doctoral, University of California, Irvine.
