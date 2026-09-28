export const especieTexto = (e) => ({ perro: 'Perro', gato: 'Gato', ave: 'Ave', otro: 'Otro' })[e] || e

export function edadTexto(meses) {
  if (meses == null) return ''
  if (meses < 12) return `${meses} ${meses === 1 ? 'mes' : 'meses'}`
  const a = Math.floor(meses / 12)
  return `${a} ${a === 1 ? 'año' : 'años'}`
}

export const fecha = (iso) =>
  iso ? new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

/** Convierte claves camelCase de detallesEspecie en etiquetas legibles. */
export const etiqueta = (k) => k.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase())
export const valor = (v) => (v === true ? 'Sí' : v === false ? 'No' : v)

/** plural(1,'postulación','postulaciones') -> "1 postulación"; plural(2, ...) -> "2 postulaciones" */
export const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

/** Concordancia de género para el estado final del animal. */
export const adoptadoTexto = (sexo) => (sexo === 'hembra' ? 'adoptada' : 'adoptado')
