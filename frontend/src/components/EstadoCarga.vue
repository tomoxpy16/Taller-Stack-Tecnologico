<script setup>
defineProps({ error: String, cargando: Boolean, vacio: Boolean, textoVacio: { type: String, default: 'No hay resultados.' } })
defineEmits(['reintentar'])
</script>

<template>
  <div v-if="cargando" class="estado-carga"><span class="spinner" /> Cargando…</div>
  <div v-else-if="error" class="alert alert--error">
    {{ error }}
    <button class="btn btn--small" @click="$emit('reintentar')">Reintentar</button>
  </div>
  <div v-else-if="vacio" class="estado-vacio">{{ textoVacio }}</div>
  <slot v-else />
</template>
