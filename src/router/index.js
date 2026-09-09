import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Reader from '../views/Reader.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/:bookId/:chapterId?',
    name: 'Reader',
    component: Reader
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0, left: 0 }
  }
})

export default router
