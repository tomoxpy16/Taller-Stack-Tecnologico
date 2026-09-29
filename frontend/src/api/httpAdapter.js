/**
 * Adaptador HTTP: habla con la API FastAPI real usando JSON:API.
 */
import { ApiError } from './errors'
import { parseDocument, toDocument } from './jsonapi'

const BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const MEDIA = 'application/vnd.api+json'

async function request(method, path, { query, body } = {}) {
  const url = new URL(BASE + path, window.location.origin)
  for (const [k, v] of Object.entries(query || {})) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  }
  let res
  try {
    res = await fetch(url, {
      method,
      headers: { Accept: MEDIA, ...(body ? { 'Content-Type': MEDIA } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, [{ code: 'RED', title: 'Sin conexión' }])
  }
  if (res.status === 204) return null
  let doc = null
  try {
    doc = await res.json()
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  if (!res.ok) throw new ApiError(res.status, doc?.errors || [{ title: res.statusText }])
  return parseDocument(doc)
}

export const httpAdapter = {
  nombre: 'http',

  async listRefugios() {
    return (await request('GET', '/refugios')).data
  },

  async listAnimals({ especie, estado, refugio, page = 1, size = 12 } = {}) {
    const r = await request('GET', '/animals', {
      query: {
        'filter[especie]': especie,
        'filter[estado]': estado,
        'filter[refugio]': refugio,
        'page[number]': page,
        'page[size]': size,
        include: 'refugio',
      },
    })
    const total = r.meta.total ?? r.data.length
    return { items: r.data, total, pages: Math.max(1, Math.ceil(total / size)) }
  },

  async getAnimal(id) {
    return (await request('GET', `/animals/${id}`, { query: { include: 'refugio' } })).data
  },

  async createAnimal(attrs, refugioId) {
    const body = toDocument('animals', attrs, { refugio: { type: 'refugios', id: refugioId } })
    return (await request('POST', '/animals', { body })).data
  },

  async registrarAdoptante(attrs) {
    return (await request('POST', '/adoptantes', { body: toDocument('adoptantes', attrs) })).data
  },

  async postular({ animalId, adoptanteId, mensaje }) {
    const body = toDocument(
      'postulaciones',
      { mensaje },
      { animal: { type: 'animals', id: animalId }, adoptante: { type: 'adoptantes', id: adoptanteId } },
    )
    return (await request('POST', '/postulaciones', { body })).data
  },

  async listPostulaciones({ refugio, adoptante, estado } = {}) {
    const r = await request('GET', '/postulaciones', {
      query: {
        'filter[refugio]': refugio,
        'filter[adoptante]': adoptante,
        'filter[estado]': estado,
        include: 'animal,adoptante',
      },
    })
    return r.data
  },

  /** Aprueba o rechaza. Devuelve { postulacion, animal, cerradas[] } */
  async resolverPostulacion(id, estado) {
    const r = await request('PATCH', `/postulaciones/${id}`, {
      body: toDocument('postulaciones', { estado }, {}, id),
    })
    const animal = r.included.find((x) => x.type === 'animals') || null
    const cerradas = r.included.filter((x) => x.type === 'postulaciones')
    return { postulacion: r.data, animal, cerradas }
  },
}
