<script setup>
import EstadoChip from './EstadoChip.vue'
import { edadTexto, especieTexto } from '../format'
defineProps({ animal: { type: Object, required: true } })
</script>

<template>
  <RouterLink :to="`/animales/${animal.id}`" class="card animal-card">
    <img :src="animal.fotos?.[0]" :alt="`Foto de ${animal.nombre}`" class="animal-card__img" />
    <div class="animal-card__body">
      <div class="animal-card__head">
        <strong>{{ animal.nombre }}</strong>
        <EstadoChip :estado="animal.estado" />
      </div>
      <div class="muted">{{ especieTexto(animal.especie) }} · {{ edadTexto(animal.edadMeses) }}</div>
      <div class="tags">
        <span v-for="t in animal.temperamento?.slice(0, 2)" :key="t" class="tag">{{ t }}</span>
      </div>
      <div v-if="animal.refugio" class="muted small">📍 {{ animal.refugio.nombre }}</div>
    </div>
  </RouterLink>
</template>
