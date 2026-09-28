<script setup>
defineProps({ estado: { type: String, required: true } })
const etiquetas = {
  disponible: 'Disponible',
  postulado: 'Con postulaciones',
  adoptado: 'Adoptado',
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
}
</script>

<template>
  <span class="chip" :class="`chip--${estado}`">{{ etiquetas[estado] || estado }}</span>
</template>
