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
  routes
})

export default router
