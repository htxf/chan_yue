<!--
  WeChatEnvNotice - 微信内置环境提示组件
  仅在微信内置浏览器内唤起，提示用户在系统浏览器中打开或添加到主屏幕以保持息屏连播
-->
<script setup>
import { ref, onMounted } from 'vue'

const isWeChat = ref(false)
const isDismissed = ref(false)

onMounted(() => {
  try {
    const ua = navigator.userAgent.toLowerCase()
    const inWechat = ua.includes('micromessenger')
    const dismissed = localStorage.getItem('chanyue_wechat_notice_dismissed') === 'true'
    isWeChat.value = inWechat
    isDismissed.value = dismissed
  } catch (e) {}
})

function dismiss() {
  isDismissed.value = true
  try {
    localStorage.setItem('chanyue_wechat_notice_dismissed', 'true')
  } catch (e) {}
}
</script>

<template>
  <transition name="notice-slide">
    <aside 
      v-if="isWeChat && !isDismissed" 
      class="wechat-notice-banner" 
      role="status" 
      aria-live="polite"
    >
      <div class="notice-inner">
        <div class="notice-main">
          <svg class="notice-icon" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span class="notice-text">
            微信内置环境受系统策略限制，息屏可能中断播放。建议点击右上角「···」选择「在浏览器打开」或「添加到主屏幕」以保持后台连播。
          </span>
        </div>
        <button class="notice-close-btn" @click="dismiss" aria-label="关闭提示">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.wechat-notice-banner {
  position: fixed;
  top: calc(10px + env(safe-area-inset-top, 0px));
  left: 14px;
  right: 14px;
  max-width: 680px;
  margin: 0 auto;
  z-index: 250;
  pointer-events: auto;
}

.notice-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px 8px 14px;
  border-radius: 10px;
  background: rgba(26, 22, 18, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(212, 165, 116, 0.28);
  box-shadow: 0 10px 24px -4px rgba(0, 0, 0, 0.6),
              0 0 0 1px rgba(255, 255, 255, 0.04);
}

.notice-main {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  flex: 1;
}

.notice-icon {
  color: var(--gold);
  flex-shrink: 0;
  margin-top: 2px;
}

.notice-text {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--text-primary);
  opacity: 0.92;
  letter-spacing: 0.2px;
}

.notice-close-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

.notice-close-btn:hover {
  background: rgba(212, 165, 116, 0.18);
  color: var(--gold);
}

.notice-close-btn:active {
  transform: scale(0.92);
}

/* 动效 */
.notice-slide-enter-active,
.notice-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.notice-slide-enter-from,
.notice-slide-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(0.98);
}

@media (max-width: 640px) {
  .wechat-notice-banner {
    top: calc(8px + env(safe-area-inset-top, 0px));
    left: 10px;
    right: 10px;
  }
  .notice-text {
    font-size: 11.5px;
    line-height: 1.45;
  }
  .notice-inner {
    padding: 7px 10px 7px 12px;
  }
}
</style>
