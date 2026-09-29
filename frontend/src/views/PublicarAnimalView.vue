<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, mensajeDe } from '../api'
import { sesion, notificar } from '../stores/sesion'

const router = useRouter()
const enviando = ref(false)
const errorGeneral = ref('')
const errores = reactive({})

const form = reactive({
  nombre: '',
  especie: 'perro',
  edadMeses: 12,
  sexo: 'hembra',
  temperamento: '',
  vacunado: false,
  esterilizado: false,
  notasSalud: '',
  fotoUrl: '',
  // detalles variables por especie (modelo documental)
  tamano: 'mediano',
  pelaje: 'corto',
  tipoAve: '',
  puedeHablar: false,
})

const detallesEspecie = computed(() => {
  if (form.especie === 'perro') return { tamano: form.tamano }
  if (form.especie === 'gato') return { pelaje: form.pelaje }
  if (form.especie === 'ave') return { tipo: form.tipoAve, puedeHablar: form.puedeHablar }
  return {}
})

async function publicar() {
  errorGeneral.value = ''
  for (const k of Object.keys(errores)) delete errores[k]
  if (!form.nombre.trim()) errores.nombre = 'El nombre es obligatorio.'
  if (!Number.isInteger(Number(form.edadMeses)) || form.edadMeses < 0) errores.edadMeses = 'Edad en meses (entero ≥ 0).'
  if (Object.keys(errores).length) return

  enviando.value = true
  try {
    const animal = await api.createAnimal(
      {
        nombre: form.nombre.trim(),
        especie: form.especie,
        edadMeses: Number(form.edadMeses),
        sexo: form.sexo,
        temperamento: form.temperamento.split(',').map((t) => t.trim()).filter(Boolean),
        salud: { vacunado: form.vacunado, esterilizado: form.esterilizado, notas: form.notasSalud },
        fotos: form.fotoUrl ? [form.fotoUrl] : [],
        detallesEspecie: detallesEspecie.value,
      },
      sesion.refugioId,
    )
    notificar(`${animal.nombre} fue publicado y ya aparece en el catálogo.`)
    router.push(`/animales/${animal.id}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) Object.assign(errores, e.fieldErrors())
    errorGeneral.value = mensajeDe(e)
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <section>
    <RouterLink to="/refugio" class="volver">← Volver al panel</RouterLink>
    <form class="publicar" novalidate @submit.prevent="publicar">
      <h1>Publicar un animal</h1>
      <p v-if="!sesion.refugioId" class="alert alert--error">Primero elige un refugio en el panel.</p>

      <div class="form-grid">
        <div class="field" :class="{ invalido: errores.nombre }">
          <label for="p-nombre">Nombre *</label>
          <input id="p-nombre" v-model="form.nombre" maxlength="60" />
          <small v-if="errores.nombre">{{ errores.nombre }}</small>
        </div>
        <div class="field">
          <label for="p-especie">Especie *</label>
          <select id="p-especie" v-model="form.especie">
            <option value="perro">Perro</option><option value="gato">Gato</option><option value="ave">Ave</option><option value="otro">Otro</option>
          </select>
        </div>
        <div class="field" :class="{ invalido: errores.edadMeses }">
          <label for="p-edad">Edad (meses) *</label>
          <input id="p-edad" v-model.number="form.edadMeses" type="number" min="0" />
          <small v-if="errores.edadMeses">{{ errores.edadMeses }}</small>
        </div>
        <div class="field">
          <label for="p-sexo">Sexo *</label>
          <select id="p-sexo" v-model="form.sexo"><option value="hembra">Hembra</option><option value="macho">Macho</option></select>
        </div>
      </div>

      <fieldset class="panel">
        <legend>Detalles de {{ form.especie }}</legend>
        <p class="muted small">Estos campos cambian según la especie: se guardan en <code>detallesEspecie</code> del documento en MongoDB.</p>
        <div v-if="form.especie === 'perro'" class="field">
          <label>Tamaño</label>
          <select v-model="form.tamano"><option>pequeño</option><option>mediano</option><option>grande</option></select>
        </div>
        <div v-else-if="form.especie === 'gato'" class="field">
          <label>Pelaje</label>
          <select v-model="form.pelaje"><option>corto</option><option>largo</option></select>
        </div>
        <div v-else-if="form.especie === 'ave'" class="form-grid">
          <div class="field"><label>Tipo de ave</label><input v-model="form.tipoAve" placeholder="periquito, canario…" /></div>
          <label class="check"><input v-model="form.puedeHablar" type="checkbox" /> Puede hablar</label>
        </div>
        <p v-else class="muted">Sin campos adicionales.</p>
      </fieldset>

      <div class="field">
        <label for="p-temp">Temperamento <span class="muted">(separado por comas)</span></label>
        <input id="p-temp" v-model="form.temperamento" placeholder="juguetón, sociable" />
      </div>

      <fieldset class="panel">
        <legend>Salud</legend>
        <label class="check"><input v-model="form.vacunado" type="checkbox" /> Vacunado</label>
        <label class="check"><input v-model="form.esterilizado" type="checkbox" /> Esterilizado</label>
        <div class="field"><label>Notas</label><input v-model="form.notasSalud" /></div>
      </fieldset>

      <div class="field" :class="{ invalido: errores.fotos }">
        <label for="p-foto">URL de foto</label>
        <input id="p-foto" v-model="form.fotoUrl" type="url" placeholder="https://…" />
        <small v-if="errores.fotos">{{ errores.fotos }}</small>
      </div>

      <div v-if="errorGeneral" class="alert alert--error">⚠ {{ errorGeneral }}</div>
      <div class="acciones">
        <button class="btn btn--primary btn--lg" :disabled="enviando || !sesion.refugioId">{{ enviando ? 'Publicando…' : 'Publicar' }}</button>
        <RouterLink to="/refugio" class="btn">Cancelar</RouterLink>
      </div>
    </form>
  </section>
</template>
