<script setup>
import { ref, computed, watch } from 'vue'
import { api, mensajeDe } from '../api'
import { sesion } from '../stores/sesion'
import EstadoChip from '../components/EstadoChip.vue'
import EstadoCarga from '../components/EstadoCarga.vue'
import { edadTexto, especieTexto, etiqueta, valor } from '../format'

const props = defineProps({ id: String })
const animal = ref(null)
const fotoActiva = ref(0)
const cargando = ref(true)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    animal.value = await api.getAnimal(props.id)
    fotoActiva.value = 0
  } catch (e) {
    error.value = mensajeDe(e)
  } finally {
    cargando.value = false
  }
}
watch(() => props.id, cargar, { immediate: true })

const adoptado = computed(() => animal.value?.estado === 'adoptado')
const detalles = computed(() => Object.entries(animal.value?.detallesEspecie || {}))
</script>

<template>
  <section>
    <RouterLink to="/animales" class="volver">← Volver al catálogo</RouterLink>
    <EstadoCarga :cargando="cargando" :error="error" @reintentar="cargar">
      <div v-if="animal" class="ficha">
        <div class="ficha__galeria">
          <img :src="animal.fotos?.[fotoActiva]" :alt="`Foto de ${animal.nombre}`" class="ficha__foto" />
          <div v-if="animal.fotos?.length > 1" class="ficha__miniaturas">
            <button v-for="(f, i) in animal.fotos" :key="i" :class="{ activa: i === fotoActiva }" @click="fotoActiva = i">
              <img :src="f" :alt="`Foto ${i + 1}`" />
            </button>
          </div>
        </div>

        <div class="ficha__info">
          <div class="ficha__titulo">
            <h1>{{ animal.nombre }}</h1>
            <EstadoChip :estado="animal.estado" />
          </div>
          <p class="lead">
            {{ especieTexto(animal.especie) }} · {{ animal.sexo === 'hembra' ? 'Hembra' : 'Macho' }} · {{ edadTexto(animal.edadMeses) }}
          </p>

          <div class="panel">
            <h3>Temperamento</h3>
            <div class="tags"><span v-for="t in animal.temperamento" :key="t" class="tag">{{ t }}</span></div>
          </div>

          <div class="panel">
            <h3>Salud</h3>
            <p>
              {{ animal.salud?.vacunado ? '✅' : '⬜' }} Vacunado &nbsp;·&nbsp;
              {{ animal.salud?.esterilizado ? '✅' : '⬜' }} Esterilizado
            </p>
            <p v-if="animal.salud?.notas" class="muted">{{ animal.salud.notas }}</p>
          </div>

          <div v-if="detalles.length" class="panel">
            <h3>Detalles de la especie</h3>
            <dl class="detalles">
              <template v-for="[k, v] in detalles" :key="k"><dt>{{ etiqueta(k) }}</dt><dd>{{ valor(v) }}</dd></template>
            </dl>
          </div>

          <div v-if="animal.refugio" class="panel">
            <h3>Refugio</h3>
            <p><strong>{{ animal.refugio.nombre }}</strong> · {{ animal.refugio.ciudad }}</p>
          </div>

          <div class="ficha__cta">
            <p v-if="adoptado" class="alert alert--info">🏡 {{ animal.nombre }} ya encontró un hogar.</p>
            <p v-else-if="sesion.rol === 'refugio'" class="muted">Cambia al rol "Adoptante" para postularte.</p>
            <RouterLink v-else :to="`/animales/${animal.id}/postular`" class="btn btn--primary btn--lg">
              Postularme para adoptar a {{ animal.nombre }}
            </RouterLink>
          </div>
        </div>
      </div>
    </EstadoCarga>
  </section>
</template>
