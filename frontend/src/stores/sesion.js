import { reactive, watch } from 'vue'

/**
 * Sesión simulada (el taller no pide autenticación).
 * - rol: 'adoptante' | 'refugio'
 * - refugioId: refugio con el que se opera el panel
 * - adoptante: se guarda tras la primera postulación para "Mis postulaciones"
 */
const KEY = 'adopta.sesion'

function cargar() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {}
  } catch {
    return {}
  }
}

export const sesion = reactive({ rol: 'adoptante', refugioId: null, adoptante: null, ...cargar() })

watch(
  sesion,
  (s) => {
    try {
      localStorage.setItem(KEY, JSON.stringify(s))
    } catch {
      /* almacenamiento no disponible: la sesión vive solo en memoria */
    }
  },
  { deep: true },
)

/** Notificaciones tipo toast */
export const toasts = reactive([])
let tid = 0
export function notificar(texto, tipo = 'ok', ms = 4000) {
  const id = ++tid
  toasts.push({ id, texto, tipo })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, ms)
}
