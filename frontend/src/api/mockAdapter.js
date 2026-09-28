/**
 * Adaptador MOCK: misma interfaz que httpAdapter, datos en memoria.
 * Replica las reglas de negocio del contrato (incluido el auto-cierre)
 * y lanza los mismos ApiError, para que la UI se pueda construir y
 * probar sin depender del backend.
 */
import { ApiError } from './errors'
import * as seed from './mockData'
import { adoptadoTexto } from '../format'

const clone = (x) => structuredClone(x)
const db = {
  refugios: clone(seed.refugios),
  animals: clone(seed.animals),
  adoptantes: clone(seed.adoptantes),
  postulaciones: clone(seed.postulaciones),
}
let seq = 100
const nuevoId = (p) => `${p}${++seq}`
const esperar = (ms = 250) => new Promise((r) => setTimeout(r, ms))

const err = (status, code, title, detail, pointer) =>
  new ApiError(status, [{ code, title, detail, source: pointer ? { pointer } : undefined }])

function porId(col, id, tipo) {
  const x = db[col].find((r) => r.id === id)
  if (!x) throw err(404, 'RECURSO_NO_ENCONTRADO', `${tipo} no encontrado`, `No existe ${tipo} con id ${id}`)
  return x
}
const conRefugio = (a) => ({ ...clone(a), refugio: clone(db.refugios.find((r) => r.id === a.refugioId)) })
const expandir = (p) => ({
  ...clone(p),
  animal: clone(db.animals.find((a) => a.id === p.animalId)),
  adoptante: clone(db.adoptantes.find((d) => d.id === p.adoptanteId)),
})

function validar(reglas) {
  const errores = []
  for (const [campo, ok, detalle] of reglas) {
    if (!ok) errores.push({ code: 'VALIDACION', title: 'Campo inválido', detail: detalle, source: { pointer: `/data/attributes/${campo}` } })
  }
  if (errores.length) throw new ApiError(422, errores)
}
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e || '')

export const mockAdapter = {
  nombre: 'mock',

  async listRefugios() {
    await esperar()
    return clone(db.refugios)
  },

  async listAnimals({ especie, estado, refugio, page = 1, size = 12 } = {}) {
    await esperar()
    let items = db.animals
      .filter((a) => (!especie || a.especie === especie) && (!estado || a.estado === estado) && (!refugio || a.refugioId === refugio))
      .sort((a, b) => b.publicadoEn.localeCompare(a.publicadoEn))
    const total = items.length
    items = items.slice((page - 1) * size, page * size).map(conRefugio)
    return { items, total, pages: Math.max(1, Math.ceil(total / size)) }
  },

  async getAnimal(id) {
    await esperar()
    return conRefugio(porId('animals', id, 'animal'))
  },

  async createAnimal(attrs, refugioId) {
    await esperar()
    porId('refugios', refugioId, 'refugio')
    validar([
      ['nombre', attrs.nombre?.trim()?.length >= 1 && attrs.nombre.length <= 60, 'El nombre es obligatorio (máx. 60).'],
      ['especie', ['perro', 'gato', 'ave', 'otro'].includes(attrs.especie), 'Especie inválida.'],
      ['edadMeses', Number.isInteger(attrs.edadMeses) && attrs.edadMeses >= 0, 'La edad debe ser un entero ≥ 0.'],
      ['sexo', ['macho', 'hembra'].includes(attrs.sexo), 'Sexo inválido.'],
    ])
    const a = { ...clone(attrs), id: nuevoId('a'), estado: 'disponible', publicadoEn: new Date().toISOString(), refugioId }
    db.animals.push(a)
    return conRefugio(a)
  },

  async registrarAdoptante(attrs) {
    await esperar(150)
    validar([
      ['nombre', attrs.nombre?.trim()?.length >= 2, 'Escribe tu nombre completo.'],
      ['email', emailOk(attrs.email), 'Ingresa un email válido.'],
      ['telefono', /^\d{7,13}$/.test(attrs.telefono || ''), 'Teléfono de 7 a 13 dígitos.'],
      ['ciudad', attrs.ciudad?.trim()?.length >= 2, 'Indica tu ciudad.'],
    ])
    const existente = db.adoptantes.find((d) => d.email.toLowerCase() === attrs.email.toLowerCase())
    if (existente) return clone(existente)
    const d = { ...clone(attrs), id: nuevoId('d') }
    db.adoptantes.push(d)
    return clone(d)
  },

  async postular({ animalId, adoptanteId, mensaje }) {
    await esperar()
    validar([['mensaje', (mensaje || '').trim().length >= 10 && mensaje.length <= 500, 'Cuéntale al refugio por qué (10 a 500 caracteres).']])
    const animal = porId('animals', animalId, 'animal')
    porId('adoptantes', adoptanteId, 'adoptante')
    // Regla 1: solo se puede postular si el animal no está adoptado.
    if (animal.estado === 'adoptado') {
      throw err(409, 'ANIMAL_NO_DISPONIBLE', 'El animal no está disponible', `${animal.nombre} ya fue ${adoptadoTexto(animal.sexo)}.`, '/data/relationships/animal')
    }
    // Regla 2: una sola postulación pendiente por adoptante y animal.
    const dup = db.postulaciones.find((p) => p.animalId === animalId && p.adoptanteId === adoptanteId && p.estado === 'pendiente')
    if (dup) {
      throw err(409, 'POSTULACION_DUPLICADA', 'Postulación duplicada', `Ya tienes una postulación pendiente para ${animal.nombre}.`)
    }
    const p = { id: nuevoId('p'), mensaje, estado: 'pendiente', motivoCierre: null, creadaEn: new Date().toISOString(), resueltaEn: null, animalId, adoptanteId }
    db.postulaciones.push(p)
    animal.estado = 'postulado'
    return expandir(p)
  },

  async listPostulaciones({ refugio, adoptante, estado } = {}) {
    await esperar()
    return db.postulaciones
      .filter((p) => {
        const a = db.animals.find((x) => x.id === p.animalId)
        return (!refugio || a?.refugioId === refugio) && (!adoptante || p.adoptanteId === adoptante) && (!estado || p.estado === estado)
      })
      .sort((a, b) => b.creadaEn.localeCompare(a.creadaEn))
      .map(expandir)
  },

  async resolverPostulacion(id, estado) {
    await esperar(400)
    if (!['aprobada', 'rechazada'].includes(estado)) {
      validar([['estado', false, 'Estado debe ser "aprobada" o "rechazada".']])
    }
    const p = porId('postulaciones', id, 'postulación')
    if (p.estado !== 'pendiente') {
      throw err(409, 'POSTULACION_YA_RESUELTA', 'Postulación ya resuelta', 'Solo se pueden resolver postulaciones pendientes.')
    }
    const animal = porId('animals', p.animalId, 'animal')
    const ahora = new Date().toISOString()
    const cerradas = []
    p.estado = estado
    p.resueltaEn = ahora
    if (estado === 'aprobada') {
      // Regla 3: auto-cierre del resto de pendientes sobre el mismo animal.
      animal.estado = 'adoptado'
      for (const otra of db.postulaciones) {
        if (otra.animalId === animal.id && otra.id !== p.id && otra.estado === 'pendiente') {
          otra.estado = 'rechazada'
          otra.motivoCierre = 'cierre_automatico'
          otra.resueltaEn = ahora
          cerradas.push(clone(otra))
        }
      }
    } else {
      p.motivoCierre = 'rechazada_por_refugio'
      const quedan = db.postulaciones.some((x) => x.animalId === animal.id && x.estado === 'pendiente')
      if (!quedan) animal.estado = 'disponible'
    }
    return { postulacion: expandir(p), animal: clone(animal), cerradas }
  },
}
