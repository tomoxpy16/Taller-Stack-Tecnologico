<script setup>
import { useRouter } from 'vue-router'
import { sesion, toasts } from './stores/sesion'

const router = useRouter()
function cambiarRol(e) {
  sesion.rol = e.target.value
  router.push(sesion.rol === 'refugio' ? '/refugio' : '/animales')
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__inner">
      <RouterLink to="/animales" class="logo">🐾 Adopta</RouterLink>
      <nav class="nav">
        <RouterLink to="/animales">Animales</RouterLink>
        <RouterLink v-if="sesion.rol === 'adoptante'" to="/mis-postulaciones">Mis postulaciones</RouterLink>
        <RouterLink v-if="sesion.rol === 'refugio'" to="/refugio">Panel refugio</RouterLink>
      </nav>
      <label class="rol">
        <span class="sr-only">Rol</span>
        <select :value="sesion.rol" @change="cambiarRol">
          <option value="adoptante">👤 Adoptante</option>
          <option value="refugio">🏠 Refugio</option>
        </select>
      </label>
    </div>
  </header>

  <main class="container">
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.fullPath" />
    </RouterView>
  </main>

  <footer class="footer muted small">
    Taller de Arquitectura · Hexagonal · Vue.js + FastAPI + MongoDB · REST / JSON:API
  </footer>

  <div class="toasts" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="`toast--${t.tipo}`">{{ t.texto }}</div>
    </TransitionGroup>
  </div>
</template>
