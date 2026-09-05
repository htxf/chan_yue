import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // 开发环境也启用 SW，方便调试
      devOptions: { enabled: true },
      // 需要被 SW 预缓存的静态资源
      includeAssets: ['favicon.svg', 'icons/*.png', 'audio/**/*'],
      manifest: {
        name: '禅阅 (ChanYue)',
        short_name: '禅阅',
        description: '极致纯粹的佛经阅读体验 — 经文展示、拼音注音、音频同步',
        lang: 'zh-CN',
        theme_color: '#1a1a1a',
        background_color: '#1a1a1a',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        skipWaiting: true,
        clientsClaim: true,
        // 运行时缓存：音频文件走 CacheFirst
        runtimeCaching: [
          {
            urlPattern: /\/audio\/.+\.(mp3|ogg|wav)$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'chan-yue-audio',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'google-fonts-stylesheets' },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-webfonts',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
})
