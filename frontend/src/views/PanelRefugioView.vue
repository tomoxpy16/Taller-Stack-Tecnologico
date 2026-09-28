<script setup>
import { ref, computed, watch } from 'vue'
import { api, mensajeDe } from '../api'
import { sesion, notificar } from '../stores/sesion'
import EstadoChip from '../components/EstadoChip.vue'
import EstadoCarga from '../components/EstadoCarga.vue'
import ConfirmModal from '../components/ConfirmModal.vue'
import { fecha, especieTexto, edadTexto, plural, adoptadoTexto } from '../format'

const refugios = ref([])
const postulaciones = ref([])
const animales = ref([])
const tab = ref('pendiente')
const cargando = ref(true)
const error = ref('')
const accion = ref(null) // { postulacion, estado }
const procesando = ref(false)
const resaltadas = ref(new Set())

const refugio = computed(() => refugios.value.find((r) => r.id === sesion.refugioId))

async function cargarRefugios() {
  try {
    refugios.value = await api.listRefugios()
    if (!sesion.refugioId && refugios.value.length) sesion.refugioId = refugios.value[0].id
  } catch (e) {
    error.value = mensajeDe(e)
    cargando.value = false
  }
}

async function cargar() {
  if (!sesion.refugioId) return
  cargando.value = true
  error.value = ''
  try {
    const [ps, as] = await Promise.all([
      api.listPostulaciones({ refugio: sesion.refugioId }),
      api.listAnimals({ refugio: sesion.refugioId, size: 50 }),
    ])
    postulaciones.value = ps
    animales.value = as.items
  } catch (e) {
    error.value = mensajeDe(e)
  } finally {
    cargando.value = false
  }
}

cargarRefugios().then(cargar)
watch(() => sesion.refugioId, cargar)

const conteo = computed(() => {
  const c = { pendiente: 0, aprobada: 0, rechazada: 0 }
  for (const p of postulaciones.value) c[p.estado]++
  return c
})
const visibles = computed(() => postulaciones.value.filter((p) => p.estado === tab.value))

/** Cuántas otras pendientes se cerrarían al aprobar esta. */
const otrasPendientes = (p) =>
  postulaciones.value.filter((x) => x.animalId === p.animalId && x.id !== p.id && x.estado === 'pendiente').length

const textoConfirmacion = computed(() => {
  if (!accion.value) return ''
  const { postulacion: p, estado } = accion.value
  const quien = p.adoptante?.nombre
  if (estado === 'rechazada') return `¿Rechazar la postulación de ${quien} para ${p.animal?.nombre}?`
  const n = otrasPendientes(p)
  return (
    `¿Aprobar a ${quien} como adoptante de ${p.animal?.nombre}? ${p.animal?.nombre} quedará como ${adoptadoTexto(p.animal?.sexo)}` +
    (n ? ` y ${n > 1 ? 'se cerrarán' : 'se cerrará'} automáticamente ${plural(n, 'postulación pendiente', 'postulaciones pendientes')}.` : '.')
  )
})

async function confirmar() {
  const { postulacion, estado } = accion.value
  procesando.value = true
  try {
    const r = await api.resolverPostulacion(postulacion.id, estado)
    aplicarResultado(r)
    const n = r.cerradas.length
    notificar(
      estado === 'aprobada'
        ? `Postulación aprobada. ${r.animal?.nombre} fue ${adoptadoTexto(r.animal?.sexo)}${n ? ` · ${plural(n, 'postulación cerrada', 'postulaciones cerradas')} automáticamente` : ''}.`
        : 'Postulación rechazada.',
    )
    accion.value = null
  } catch (e) {
    notificar(mensajeDe(e), 'error', 6000)
    accion.value = null
    cargar()
  } finally {
    procesando.value = false
  }
}

/** Actualización reactiva con la respuesta del PATCH, sin volver a pedir la lista. */
function aplicarResultado({ postulacion, animal, cerradas }) {
  const cambios = [postulacion, ...cerradas]
  for (const c of cambios) {
    const i = postulaciones.value.findIndex((p) => p.id === c.id)
    if (i >= 0) postulaciones.value[i] = { ...postulaciones.value[i], ...c, animal: postulaciones.value[i].animal, adoptante: postulaciones.value[i].adoptante }
  }
  if (animal) {
    for (const p of postulaciones.value) if (p.animalId === animal.id) p.animal = { ...p.animal, ...animal }
    const j = animales.value.findIndex((a) => a.id === animal.id)
    if (j >= 0) animales.value[j] = { ...animales.value[j], ...animal }
  }
  resaltadas.value = new Set(cambios.map((c) => c.id))
  setTimeout(() => (resaltadas.value = new Set()), 2500)
}
</script>

<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Panel del refugio</h1>
        <p class="muted" v-if="refugio">{{ refugio.nombre }} · {{ refugio.ciudad }}</p>
      </div>
      <div class="page-head__actions">
        <label class="inline">
          Refugio
          <select v-model="sesion.refugioId">
            <option v-for="r in refugios" :key="r.id" :value="r.id">{{ r.nombre }}</option>
          </select>
        </label>
        <RouterLink to="/refugio/publicar" class="btn btn--primary">+ Publicar animal</RouterLink>
      </div>
    </div>

    <div class="tabs" role="tablist">
      <button role="tab" :aria-selected="tab === 'pendiente'" :class="{ activa: tab === 'pendiente' }" @click="tab = 'pendiente'">Pendientes <span class="badge">{{ conteo.pendiente }}</span></button>
      <button role="tab" :aria-selected="tab === 'aprobada'" :class="{ activa: tab === 'aprobada' }" @click="tab = 'aprobada'">Aprobadas <span class="badge">{{ conteo.aprobada }}</span></button>
      <button role="tab" :aria-selected="tab === 'rechazada'" :class="{ activa: tab === 'rechazada' }" @click="tab = 'rechazada'">Rechazadas <span class="badge">{{ conteo.rechazada }}</span></button>
      <button role="tab" :aria-selected="tab === 'animales'" :class="{ activa: tab === 'animales' }" @click="tab = 'animales'">Mis animales <span class="badge">{{ animales.length }}</span></button>
    </div>

    <EstadoCarga :cargando="cargando" :error="error" @reintentar="cargar">
      <!-- Mis animales -->
      <div v-if="tab === 'animales'">
        <div v-if="!animales.length" class="estado-vacio">Aún no has publicado animales.</div>
        <table v-else class="tabla">
          <thead><tr><th>Animal</th><th>Especie</th><th>Edad</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-for="a in animales" :key="a.id">
              <td><strong>{{ a.nombre }}</strong></td>
              <td>{{ especieTexto(a.especie) }}</td>
              <td>{{ edadTexto(a.edadMeses) }}</td>
              <td><EstadoChip :estado="a.estado" /></td>
              <td><RouterLink :to="`/animales/${a.id}`">Ver ficha</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Postulaciones -->
      <div v-else>
        <div v-if="!visibles.length" class="estado-vacio">No hay postulaciones en este estado.</div>
        <table v-else :key="tab" class="tabla">
          <thead>
            <tr><th>Animal</th><th>Adoptante</th><th>Mensaje</th><th>Fecha</th><th>Estado</th><th v-if="tab === 'pendiente'">Acciones</th></tr>
          </thead>
          <TransitionGroup tag="tbody" name="fila">
            <tr v-for="p in visibles" :key="p.id" :class="{ resaltada: resaltadas.has(p.id) }">
              <td>
                <strong>{{ p.animal?.nombre }}</strong>
                <div><EstadoChip :estado="p.animal?.estado" /></div>
              </td>
              <td>
                {{ p.adoptante?.nombre }}
                <div class="muted small">{{ p.adoptante?.ciudad }} · {{ p.adoptante?.telefono }}</div>
              </td>
              <td class="tabla__mensaje">{{ p.mensaje }}</td>
              <td class="small">{{ fecha(p.creadaEn) }}</td>
              <td>
                <EstadoChip :estado="p.estado" />
                <div v-if="p.motivoCierre === 'cierre_automatico'" class="muted small">cierre automático</div>
              </td>
              <td v-if="tab === 'pendiente'">
                <div class="acciones-fila">
                <button class="btn btn--small btn--ok" @click="accion = { postulacion: p, estado: 'aprobada' }">✔ Aprobar</button>
                <button class="btn btn--small btn--danger-outline" @click="accion = { postulacion: p, estado: 'rechazada' }">✖ Rechazar</button>
                <div v-if="otrasPendientes(p)" class="muted small">+{{ otrasPendientes(p) }} otra{{ otrasPendientes(p) > 1 ? 's' : '' }} por {{ p.animal?.nombre }}</div>
                </div>
              </td>
            </tr>
          </TransitionGroup>
        </table>
      </div>
    </EstadoCarga>

    <ConfirmModal
      v-if="accion"
      :titulo="accion.estado === 'aprobada' ? 'Aprobar postulación' : 'Rechazar postulación'"
      :mensaje="textoConfirmacion"
      :confirmar="accion.estado === 'aprobada' ? 'Aprobar' : 'Rechazar'"
      :peligro="accion.estado === 'rechazada'"
      :cargando="procesando"
      @confirmar="confirmar"
      @cancelar="accion = null"
    />
  </section>
</template>
