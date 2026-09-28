<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, mensajeDe } from '../api'
import { sesion, notificar } from '../stores/sesion'
import EstadoChip from '../components/EstadoChip.vue'
import EstadoCarga from '../components/EstadoCarga.vue'
import { edadTexto, especieTexto } from '../format'

const props = defineProps({ id: String })
const router = useRouter()

const animal = ref(null)
const cargando = ref(true)
const errorCarga = ref('')
const enviando = ref(false)
const errorGeneral = ref('')
const errores = reactive({})
const form = reactive({
  nombre: sesion.adoptante?.nombre || '',
  email: sesion.adoptante?.email || '',
  telefono: sesion.adoptante?.telefono || '',
  ciudad: sesion.adoptante?.ciudad || '',
  mensaje: '',
})

async function cargar() {
  cargando.value = true
  errorCarga.value = ''
  try {
    animal.value = await api.getAnimal(props.id)
  } catch (e) {
    errorCarga.value = mensajeDe(e)
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

/** Validación en cliente: da feedback inmediato. El backend vuelve a validar (fuente de verdad). */
function validarLocal() {
  for (const k of Object.keys(errores)) delete errores[k]
  if (form.nombre.trim().length < 2) errores.nombre = 'Escribe tu nombre completo.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errores.email = 'Ingresa un email válido.'
  if (!/^\d{7,13}$/.test(form.telefono)) errores.telefono = 'Teléfono de 7 a 13 dígitos, sin espacios.'
  if (form.ciudad.trim().length < 2) errores.ciudad = 'Indica tu ciudad.'
  const n = form.mensaje.trim().length
  if (n < 10 || n > 500) errores.mensaje = 'Cuéntale al refugio por qué (10 a 500 caracteres).'
  return Object.keys(errores).length === 0
}

async function enviar() {
  errorGeneral.value = ''
  if (!validarLocal()) return
  enviando.value = true
  try {
    const { mensaje, ...datos } = form
    const adoptante = await api.registrarAdoptante(datos)
    sesion.adoptante = adoptante
    await api.postular({ animalId: props.id, adoptanteId: adoptante.id, mensaje })
    notificar(`¡Postulación enviada! El refugio revisará tu solicitud para ${animal.value.nombre}.`)
    router.push('/mis-postulaciones')
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) Object.assign(errores, e.fieldErrors())
    errorGeneral.value = mensajeDe(e)
    if (e instanceof ApiError && e.code === 'ANIMAL_NO_DISPONIBLE') cargar()
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <section>
    <RouterLink :to="`/animales/${id}`" class="volver">← Volver a la ficha</RouterLink>
    <EstadoCarga :cargando="cargando" :error="errorCarga" @reintentar="cargar">
      <div v-if="animal" class="postular">
        <aside class="card postular__resumen">
          <img :src="animal.fotos?.[0]" :alt="animal.nombre" />
          <div class="animal-card__body">
            <div class="muted small">Postulando a</div>
            <div class="animal-card__head"><strong>{{ animal.nombre }}</strong><EstadoChip :estado="animal.estado" /></div>
            <div class="muted">{{ especieTexto(animal.especie) }} · {{ edadTexto(animal.edadMeses) }}</div>
          </div>
        </aside>

        <form class="postular__form" novalidate @submit.prevent="enviar">
          <h1>Tus datos</h1>
          <p class="muted">No necesitas cuenta. Si ya te postulaste antes con este email, usaremos tus datos guardados.</p>

          <div class="form-grid">
            <div class="field" :class="{ invalido: errores.nombre }">
              <label for="nombre">Nombre completo *</label>
              <input id="nombre" v-model="form.nombre" autocomplete="name" />
              <small v-if="errores.nombre">{{ errores.nombre }}</small>
            </div>
            <div class="field" :class="{ invalido: errores.email }">
              <label for="email">Email *</label>
              <input id="email" v-model="form.email" type="email" autocomplete="email" />
              <small v-if="errores.email">{{ errores.email }}</small>
            </div>
            <div class="field" :class="{ invalido: errores.telefono }">
              <label for="telefono">Teléfono *</label>
              <input id="telefono" v-model="form.telefono" inputmode="numeric" autocomplete="tel" />
              <small v-if="errores.telefono">{{ errores.telefono }}</small>
            </div>
            <div class="field" :class="{ invalido: errores.ciudad }">
              <label for="ciudad">Ciudad *</label>
              <input id="ciudad" v-model="form.ciudad" autocomplete="address-level2" />
              <small v-if="errores.ciudad">{{ errores.ciudad }}</small>
            </div>
          </div>

          <div class="field" :class="{ invalido: errores.mensaje }">
            <label for="mensaje">¿Por qué quieres adoptar a {{ animal.nombre }}? *</label>
            <textarea id="mensaje" v-model="form.mensaje" rows="5" maxlength="500" />
            <small v-if="errores.mensaje">{{ errores.mensaje }}</small>
            <span class="contador">{{ form.mensaje.length }}/500</span>
          </div>

          <div v-if="errorGeneral" class="alert alert--error">
            ⚠ {{ errorGeneral }}
            <RouterLink v-if="errorGeneral.includes('pendiente')" to="/mis-postulaciones">Ver mis postulaciones</RouterLink>
          </div>

          <div class="acciones">
            <button class="btn btn--primary btn--lg" :disabled="enviando || animal.estado === 'adoptado'">
              {{ enviando ? 'Enviando…' : 'Enviar postulación' }}
            </button>
            <RouterLink :to="`/animales/${id}`" class="btn">Cancelar</RouterLink>
          </div>
        </form>
      </div>
    </EstadoCarga>
  </section>
</template>
