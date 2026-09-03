<!--
  AudioPlayer - 底部固定音频播放控制条
  磨砂玻璃效果，极简禅风设计
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentTime: Number,
  duration: Number,
  isPlaying: Boolean,
  progress: Number,
  autoPlay: Boolean,
  voice: {
    type: String,
    default: 'female'
  }
})

const emit = defineEmits(['toggle', 'seek', 'update:autoPlay', 'update:voice'])

/** 格式化时间 mm:ss */
function fmt(sec) {
  if (!sec || isNaN(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const timeDisplay = computed(() => `${fmt(props.currentTime)} / ${fmt(props.duration)}`)

/** 进度条点击 seek */
function onProgressClick(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  emit('seek', Math.max(0, Math.min(100, pct)))
}
</script>

<template>
  <div class="audio-player" id="audio-player">
    <button
      id="play-btn"
      class="play-btn"
      :class="{ playing: isPlaying }"
      @click="emit('toggle')"
      :aria-label="isPlaying ? '暂停' : '播放'"
    >
      <!-- 播放图标 -->
      <svg v-if="!isPlaying" viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
        <path d="M8 5v14l11-7z"/>
      </svg>
      <!-- 暂停图标 -->
      <svg v-else viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
        <rect x="6" y="4" width="4" height="16" rx="1"/>
        <rect x="14" y="4" width="4" height="16" rx="1"/>
      </svg>
    </button>

    <div class="progress-area" @click="onProgressClick">
      <div class="progress-track">
        <div
          class="progress-fill"
          :style="{ width: `${progress}%` }"
        ></div>
        <div
          class="progress-thumb"
          :style="{ left: `${progress}%` }"
        ></div>
      </div>
    </div>

    <span class="time-display">{{ timeDisplay }}</span>
    
    <button 
      class="voice-btn" 
      @click="emit('update:voice', voice === 'female' ? 'male' : 'female')"
      :title="voice === 'female' ? '当前音色：清平女声（Zephyr），点击切换为沉稳男声' : '当前音色：沉稳男声（Charon），点击切换为清平女声'"
    >
      <!-- 清平女声：莲花花蕾细线图标 -->
      <svg v-if="voice === 'female'" class="voice-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
        <path d="M12 3a9 9 0 0 0-9 9c0 4.97 4.03 9 9 9s9-4.03 9-9a9 9 0 0 0-9-9z" opacity="0.3"/>
        <path d="M12 7c-2 2.5-3 5-3 7a3 3 0 0 0 6 0c0-2-1-4.5-3-7z"/>
      </svg>
      <!-- 沉稳男声：禅钟/山岳细线图标 -->
      <svg v-else class="voice-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
        <path d="M4 20h16"/>
        <path d="M6 20v-7a6 6 0 0 1 12 0v7"/>
        <path d="M12 4v3"/>
      </svg>
      <span>{{ voice === 'female' ? '女声' : '男声' }}</span>
    </button>

    <button 
      class="auto-play-btn" 
      :class="autoPlay ? 'is-on' : 'is-off'"
      @click="emit('update:autoPlay', !autoPlay)"
      :title="autoPlay ? '自动连播：已开启' : '自动连播：已关闭'"
    >
      <!-- 连播：循环回溯细线图标 -->
      <svg class="loop-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="12" height="12">
        <path d="M17 2l4 4-4 4"/>
        <path d="M3 11v-1a4 4 0 0 1 4-4h14"/>
        <path d="M7 22l-4-4 4-4"/>
        <path d="M21 13v1a4 4 0 0 1-4 4H3"/>
      </svg>
      <span>{{ autoPlay ? '连播' : '单品' }}</span>
    </button>
  </div>
</template>

<style scoped>
.audio-player {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 680px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 20px;
  border-radius: 9999px;
  background: rgba(15, 15, 23, 0.84);
  backdrop-filter: blur(28px) saturate(1.6);
  -webkit-backdrop-filter: blur(28px) saturate(1.6);
  border: 1px solid rgba(212, 165, 116, 0.16);
  box-shadow:
    0 16px 36px -4px rgba(0, 0, 0, 0.65),
    0 0 0 1px rgba(255, 255, 255, 0.04),
    0 0 24px rgba(212, 165, 116, 0.06);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.audio-player::before {
  content: '';
  position: absolute;
  top: 0;
  left: 18%;
  right: 18%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.45), transparent);
  pointer-events: none;
}

.play-btn {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1.5px solid var(--gold-dim);
  background: rgba(212, 165, 116, 0.08);
  color: var(--gold);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.play-btn:hover {
  background: rgba(212, 165, 116, 0.18);
  border-color: var(--gold-muted);
  transform: scale(1.05);
}

.play-btn.playing {
  border-color: var(--gold);
  background: rgba(212, 165, 116, 0.14);
}

.progress-area {
  flex: 1;
  padding: 8px 0;
  cursor: pointer;
}

.progress-track {
  position: relative;
  height: 3px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: visible;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--gold-dim), var(--gold));
  border-radius: 2px;
  transition: width 0.1s linear;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%) scale(0);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--gold);
  transition: transform 0.2s ease;
  box-shadow: 0 0 10px rgba(212, 165, 116, 0.5);
}

.progress-area:hover .progress-thumb {
  transform: translate(-50%, -50%) scale(1);
}

.time-display {
  flex-shrink: 0;
  font-family: 'Noto Serif SC', monospace;
  font-size: 12px;
  color: var(--text-muted);
  min-width: 76px;
  text-align: right;
  letter-spacing: 0.5px;
}

.auto-play-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 8px;
  transition: all 0.25s ease;
}

.auto-play-btn.is-on {
  color: rgba(212, 175, 55, 0.9);
  background: rgba(212, 175, 55, 0.06);
}

.auto-play-btn.is-off {
  color: var(--text-muted);
}

.auto-play-btn:hover {
  color: var(--text-primary);
  background: rgba(212, 165, 116, 0.08);
}

.voice-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(212, 175, 55, 0.06);
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 14px;
  cursor: pointer;
  padding: 4px 10px;
  font-size: 12px;
  font-family: 'Noto Serif SC', serif;
  color: rgba(212, 175, 55, 0.9);
  transition: all 0.25s ease;
}

.voice-btn:hover {
  background: rgba(212, 175, 55, 0.16);
  border-color: rgba(212, 175, 55, 0.5);
  color: #fff;
  transform: translateY(-1px);
}

@media (max-width: 640px) {
  .audio-player {
    bottom: calc(12px + env(safe-area-inset-bottom, 0px));
    width: calc(100% - 20px);
    padding: 8px 12px;
    gap: 8px;
    border-radius: 28px;
  }
  .play-btn {
    width: 36px;
    height: 36px;
  }
  .time-display {
    font-size: 11px;
    min-width: 62px;
  }
  .voice-btn, .auto-play-btn {
    font-size: 11px;
    padding: 3px 6px;
    gap: 2px;
  }
}
</style>
