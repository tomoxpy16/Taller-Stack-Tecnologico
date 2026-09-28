/**
 * Puerto de la SPA hacia el backend.
 *
 * Las vistas SOLO importan `api` desde aquí. Qué adaptador hay detrás
 * (HTTP real o mock en memoria) se decide por configuración, igual que
 * en el backend hexagonal se decide qué repositorio inyectar con Depends().
 *
 *   npm run dev        -> API real (/api/v1)
 *   npm run dev:mock   -> datos mock, sin backend
 */
import { httpAdapter } from './httpAdapter'
import { mockAdapter } from './mockAdapter'

export const usandoMock = import.meta.env.VITE_USE_MOCK === 'true'
export const api = usandoMock ? mockAdapter : httpAdapter

export { ApiError, mensajeDe } from './errors'
