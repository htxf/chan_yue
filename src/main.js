import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import { registerSW } from 'virtual:pwa-register'

// 清理旧版被 SW 错误缓存的音频分片，确保直通原生 HTTP 管道
if (typeof window !== 'undefined' && 'caches' in window) {
  caches.delete('chan-yue-audio-v2').catch(() => {})
  caches.delete('chan-yue-audio-v1').catch(() => {})
}

registerSW({ immediate: true })

createApp(App).use(router).mount('#app')
