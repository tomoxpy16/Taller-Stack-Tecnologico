import { createRouter, createWebHistory } from 'vue-router'
import { sesion } from './stores/sesion'

const routes = [
  { path: '/', redirect: '/animales' },
  { path: '/animales', name: 'catalogo', component: () => import('./views/CatalogoView.vue'), meta: { titulo: 'Animales' } },
  { path: '/animales/:id', name: 'ficha', component: () => import('./views/FichaView.vue'), props: true, meta: { titulo: 'Ficha' } },
  { path: '/animales/:id/postular', name: 'postular', component: () => import('./views/PostularView.vue'), props: true, meta: { titulo: 'Postulación', rol: 'adoptante' } },
  { path: '/mis-postulaciones', name: 'mis-postulaciones', component: () => import('./views/MisPostulacionesView.vue'), meta: { titulo: 'Mis postulaciones', rol: 'adoptante' } },
  { path: '/refugio', name: 'panel', component: () => import('./views/PanelRefugioView.vue'), meta: { titulo: 'Panel del refugio', rol: 'refugio' } },
  { path: '/refugio/publicar', name: 'publicar', component: () => import('./views/PublicarAnimalView.vue'), meta: { titulo: 'Publicar animal', rol: 'refugio' } },
  { path: '/:pathMatch(.*)*', name: 'no-encontrado', component: () => import('./views/NoEncontradoView.vue'), meta: { titulo: 'No encontrado' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// Si se entra a una ruta de otro rol, se cambia el rol simulado automáticamente.
router.beforeEach((to) => {
  if (to.meta.rol && sesion.rol !== to.meta.rol) sesion.rol = to.meta.rol
})
router.afterEach((to) => {
  document.title = `${to.meta.titulo || 'Adopta'} · Adopta`
})

export default router
