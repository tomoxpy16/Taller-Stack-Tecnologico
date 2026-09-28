<script setup>
import { ref, onMounted } from 'vue'
import { api, mensajeDe } from '../api'
import { sesion } from '../stores/sesion'
import EstadoChip from '../components/EstadoChip.vue'
import EstadoCarga from '../components/EstadoCarga.vue'
import { fecha } from '../format'

const lista = ref([])
const cargando = ref(true)
const error = ref('')

async function cargar() {
  if (!sesion.adoptante) {
    cargando.value = false
    return
  }
  cargando.value = true
  error.value = ''
  try {
    lista.value = await api.listPostulaciones({ adoptante: sesion.adoptante.id })
  } catch (e) {
    error.value = mensajeDe(e)
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

const explicacion = (p) =>
  p.estado === 'aprobada'
    ? '¡Felicidades! El refugio aprobó tu postulación y te contactará.'
    : p.motivoCierre === 'cierre_automatico'
      ? 'El refugio aprobó a otro adoptante para este animal.'
      : p.estado === 'rechazada'
        ? 'El refugio no aprobó esta postulación.'
        : 'El refugio está revisando tu postulación.'
</script>

<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Mis postulaciones</h1>
        <p v-if="sesion.adoptante" class="muted">Seguimiento de las solicitudes de {{ sesion.adoptante.nombre }}.</p>
      </div>
    </div>

    <div v-if="!sesion.adoptante" class="estado-vacio">
      Aún no te has postulado a ningún animal. <RouterLink to="/animales">Ver animales disponibles</RouterLink>
    </div>

    <EstadoCarga v-else :cargando="cargando" :error="error" :vacio="!lista.length" texto-vacio="No tienes postulaciones todavía." @reintentar="cargar">
      <ul class="seguimiento">
        <li v-for="p in lista" :key="p.id" class="card seguimiento__item">
          <img :src="p.animal?.fotos?.[0]" :alt="p.animal?.nombre" />
          <div class="seguimiento__body">
            <div class="animal-card__head">
              <RouterLink :to="`/animales/${p.animalId}`"><strong>{{ p.animal?.nombre }}</strong></RouterLink>
              <EstadoChip :estado="p.estado" />
            </div>
            <p>{{ explicacion(p) }}</p>
            <p class="muted small">Enviada el {{ fecha(p.creadaEn) }}<span v-if="p.resueltaEn"> · Resuelta el {{ fecha(p.resueltaEn) }}</span></p>
          </div>
        </li>
      </ul>
    </EstadoCarga>
  </section>
</template>
