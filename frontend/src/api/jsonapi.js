/**
 * Utilidades para convertir documentos JSON:API <-> objetos planos
 * que usan las vistas. Así los componentes nunca manipulan
 * `data.attributes` ni `relationships` directamente.
 */

const camel = (k) => k.replace(/_([a-z])/g, (_, c) => c.toUpperCase())

/** Nombres alternativos que puede usar el backend -> nombre que usan las vistas. */
const ALIAS = {
  fechaPublicacion: 'publicadoEn',
  fechaPostulacion: 'creadaEn',
  fechaResolucion: 'resueltaEn',
}

/**
 * Traductor en el borde (anti-corruption layer del frontend): acepta
 * snake_case o camelCase, fotos como URL o como { url, descripcion },
 * y la ciudad del refugio dentro de `direccion`. Las vistas siempre
 * reciben la misma forma, sin importar cómo serialice el backend.
 */
export function normalizar(obj) {
  const out = {}
  for (const [k, v] of Object.entries(obj)) {
    const c = camel(k)
    out[ALIAS[c] || c] = v
  }
  if (Array.isArray(out.fotos)) out.fotos = out.fotos.map((f) => (typeof f === 'string' ? f : f?.url)).filter(Boolean)
  if (!out.ciudad && out.direccion?.ciudad) out.ciudad = out.direccion.ciudad
  if (!out.motivoCierre && out.motivoRechazo) {
    out.motivoCierre = /autom/i.test(out.motivoRechazo) ? 'cierre_automatico' : 'rechazada_por_refugio'
  }
  if (out.type === 'animales') out.type = 'animals'
  return out
}

/** Recurso JSON:API -> objeto plano { id, ...attributes, <rel>Id } */
export function flatten(resource) {
  if (!resource) return null
  const obj = normalizar({ id: resource.id, type: resource.type, ...(resource.attributes || {}) })
  for (const [name, rel] of Object.entries(resource.relationships || {})) {
    if (rel?.data && !Array.isArray(rel.data)) obj[`${camel(name)}Id`] = rel.data.id
  }
  return obj
}

/** Índice de `included` por "type:id" */
export function indexIncluded(included = []) {
  const map = new Map()
  for (const r of included) {
    const f = flatten(r)
    map.set(`${f.type}:${f.id}`, f)
  }
  return map
}

/** Adjunta a cada objeto plano sus relaciones to-one resueltas desde `included`. */
export function attachIncluded(resource, flat, idx) {
  for (const [name, rel] of Object.entries(resource.relationships || {})) {
    const d = rel?.data
    if (d && !Array.isArray(d)) {
      const type = d.type === 'animales' ? 'animals' : d.type
      const hit = idx.get(`${type}:${d.id}`)
      if (hit) flat[camel(name)] = hit
    }
  }
  return flat
}

/** Documento completo -> { data: objeto|objeto[], included: Map, meta, links } */
export function parseDocument(doc) {
  const idx = indexIncluded(doc.included)
  const conv = (r) => attachIncluded(r, flatten(r), idx)
  const data = Array.isArray(doc.data) ? doc.data.map(conv) : conv(doc.data)
  return { data, included: [...idx.values()], meta: doc.meta || {}, links: doc.links || {} }
}

/** Construye el cuerpo de un POST/PATCH JSON:API. */
export function toDocument(type, attributes, relationships = {}, id) {
  const rels = {}
  for (const [name, ref] of Object.entries(relationships)) {
    if (ref) rels[name] = { data: { type: ref.type, id: ref.id } }
  }
  const data = { type, attributes }
  if (id) data.id = id
  if (Object.keys(rels).length) data.relationships = rels
  return { data }
}
