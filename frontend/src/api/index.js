/**
 * Puerto de la SPA hacia el backend.
 *
 * Las vistas SOLO importan `api` desde aquí. El adaptador es el HTTP real contra la API
 * JSON:API (/api/v1). No hay datos simulados: si el backend no responde, las vistas
 * muestran el error en lugar de datos falsos.
 */
import { httpAdapter } from './httpAdapter'

export const api = httpAdapter
export { ApiError, mensajeDe } from './errors'
