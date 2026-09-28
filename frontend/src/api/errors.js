/**
 * Error uniforme que devuelven ambos adaptadores (HTTP y mock).
 * Refleja el objeto `errors[]` de JSON:API para que las vistas
 * manejen igual un 409 real que uno simulado.
 */
export class ApiError extends Error {
  constructor(status, errors = []) {
    super(errors[0]?.detail || errors[0]?.title || `Error ${status}`)
    this.status = status
    this.errors = errors.map((e) => ({
      code: e.code,
      title: e.title,
      detail: e.detail,
      pointer: e.source?.pointer ?? e.pointer ?? null,
    }))
  }

  get code() {
    return this.errors[0]?.code
  }

  /** Errores de validación agrupados por campo: { mensaje: '...', email: '...' } */
  fieldErrors() {
    const out = {}
    for (const e of this.errors) {
      if (!e.pointer) continue
      const campo = e.pointer.split('/').pop()
      out[campo] = e.detail || e.title
    }
    return out
  }
}

/** Mensajes amigables para los códigos de dominio del contrato. */
export const MENSAJES = {
  ANIMAL_NO_DISPONIBLE: 'Este animal ya no está disponible para adopción.',
  POSTULACION_DUPLICADA: 'Ya tienes una postulación pendiente para este animal.',
  POSTULACION_YA_RESUELTA: 'Esta postulación ya fue resuelta por otra persona. Recarga la página.',
  RECURSO_NO_ENCONTRADO: 'No encontramos lo que buscas.',
  VALIDACION: 'Revisa los campos marcados.',
  RED: 'No se pudo conectar con el servidor. ¿Está corriendo el backend?',
}

export function mensajeDe(err) {
  if (err instanceof ApiError) return MENSAJES[err.code] || err.message
  return MENSAJES.RED
}
