<!--
  ModeSelector - 阅读模式切换器
  阅读 / 禅听 两种模式
-->
<script setup>
defineProps({
  mode: String,
})

const emit = defineEmits(['update:mode'])

const modes = [
  { key: 'reading', label: '阅读' },
  { key: 'listening', label: '禅听' },
]
</script>

<template>
  <nav class="mode-selector" id="mode-selector">
    <button
      v-for="m in modes"
      :key="m.key"
      :id="`mode-${m.key}`"
      class="mode-btn"
      :class="{ active: mode === m.key }"
      @click="emit('update:mode', m.key)"
    >
      <span class="mode-icon">
        <!-- 阅读：经卷书册图标 -->
        <svg v-if="m.key === 'reading'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          <line x1="8" y1="7" x2="16" y2="7" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
        <!-- 禅听：引磬钟音图标 -->
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </span>
      <span class="mode-label">{{ m.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.mode-selector {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 0 20px 36px;
  animation: fadeIn 1s ease 0.5s both;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border: 1px solid transparent;
  border-radius: 20px;
  background: transparent;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.35s ease;
  letter-spacing: 1px;
}

.mode-btn:hover {
  color: var(--text-primary);
  background: rgba(212, 165, 116, 0.05);
}

.mode-btn.active {
  color: var(--gold);
  border-color: var(--gold-dim);
  background: rgba(212, 165, 116, 0.08);
}

.mode-icon {
  font-size: 14px;
  line-height: 1;
}

.mode-label {
  line-height: 1;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 640px) {
  .mode-btn {
    padding: 6px 14px;
    font-size: 12px;
  }
}
</style>
