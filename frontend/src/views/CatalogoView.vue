<script setup>
import { ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, mensajeDe } from '../api'
import AnimalCard from '../components/AnimalCard.vue'
import EstadoCarga from '../components/EstadoCarga.vue'

const route = useRoute()
const router = useRouter()

// Los filtros viven en la URL: se pueden compartir y el botón "atrás" funciona.
const filtros = reactive({
  especie: route.query.especie || '',
  estado: route.query.estado ?? 'disponible',
  page: Number(route.query.page) || 1,
})
const animales = ref([])
const total = ref(0)
const paginas = ref(1)
const cargando = ref(true)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const r = await api.listAnimals({ ...filtros, size: 8 })
    animales.value = r.items
    total.value = r.total
    paginas.value = r.pages
  } catch (e) {
    error.value = mensajeDe(e)
  } finally {
    cargando.value = false
  }
}

watch(
  () => ({ ...filtros }),
  (f, antes) => {
    if (antes && (f.especie !== antes.especie || f.estado !== antes.estado)) filtros.page = 1
    router.replace({ query: { ...filtros } })
    cargar()
  },
  { immediate: true },
)
</script>

<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Encuentra a tu nuevo compañero</h1>
        <p class="muted">Animales publicados por refugios aliados. Postúlate y el refugio te contactará.</p>
      </div>
    </div>

    <div class="filtros">
      <label>
        Especie
        <select v-model="filtros.especie">
          <option value="">Todas</option>
          <option value="perro">Perros</option>
          <option value="gato">Gatos</option>
          <option value="ave">Aves</option>
          <option value="otro">Otros</option>
        </select>
      </label>
      <label>
        Estado
        <select v-model="filtros.estado">
          <option value="">Todos</option>
          <option value="disponible">Disponible</option>
          <option value="postulado">Con postulaciones</option>
          <option value="adoptado">Adoptado</option>
        </select>
      </label>
      <span class="muted filtros__total" v-if="!cargando && !error">{{ total }} resultado{{ total === 1 ? '' : 's' }}</span>
    </div>

    <EstadoCarga :cargando="cargando" :error="error" :vacio="!animales.length" texto-vacio="No hay animales con esos filtros." @reintentar="cargar">
      <div class="grid">
        <AnimalCard v-for="a in animales" :key="a.id" :animal="a" />
      </div>
      <nav v-if="paginas > 1" class="paginador">
        <button class="btn btn--small" :disabled="filtros.page <= 1" @click="filtros.page--">‹ Anterior</button>
        <span>Página {{ filtros.page }} de {{ paginas }}</span>
        <button class="btn btn--small" :disabled="filtros.page >= paginas" @click="filtros.page++">Siguiente ›</button>
      </nav>
    </EstadoCarga>
  </section>
</template>
