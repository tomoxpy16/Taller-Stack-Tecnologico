<script setup>
defineProps({
  titulo: String,
  mensaje: String,
  confirmar: { type: String, default: 'Confirmar' },
  peligro: Boolean,
  cargando: Boolean,
})
defineEmits(['confirmar', 'cancelar'])
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('cancelar')">
    <div class="modal" role="dialog" aria-modal="true">
      <h3>{{ titulo }}</h3>
      <p>{{ mensaje }}</p>
      <div class="modal__actions">
        <button class="btn" :disabled="cargando" @click="$emit('cancelar')">Cancelar</button>
        <button class="btn" :class="peligro ? 'btn--danger' : 'btn--primary'" :disabled="cargando" @click="$emit('confirmar')">
          {{ cargando ? 'Procesando…' : confirmar }}
        </button>
      </div>
    </div>
  </div>
</template>
