<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAudioSync } from '../composables/useAudioSync'
import catalog from '../data/catalog.json'

const router = useRouter()

// --- 经卷与品目状态 ---
const selectedBookId = ref(localStorage.getItem('chanyue_listen_book') || 'xinjing')
const selectedChapterId = ref(localStorage.getItem('chanyue_listen_chapter') || 'chapter_1')

const bookMeta = ref(null)
const chapterData = ref(null)
const isLoading = ref(false)

// 章节列表
const chaptersList = computed(() => bookMeta.value?.chapters || [])

// 当前段落数组
const paragraphsRef = computed(() => chapterData.value?.paragraphs || [])

// 音色偏好
const selectedVoice = ref(localStorage.getItem('chanyue_voice') || 'female')

function getVoiceAudioUrl(rawUrl, voice = selectedVoice.value) {
  if (!rawUrl) return rawUrl
  if (rawUrl.endsWith('.mp3')) {
    const base = rawUrl.slice(0, -4).replace(/_(female|male)$/, '')
    return `${base}_${voice}.mp3`
  }
  return rawUrl
}

// 播放模式: 'sequence' (连播全卷) | 'single' (单品听诵) | 'repeat-one' (循环持诵)
const playMode = ref(localStorage.getItem('chanyue_listen_mode') || 'sequence')
watch(playMode, (val) => {
  localStorage.setItem('chanyue_listen_mode', val)
})

// 禅修定时 (分钟): 0(不限), 15, 30, 45, -1(播完本品)
const sleepTimerMinutes = ref(0)
const sleepTimerRemaining = ref(0)
let sleepTimerInterval = null

const timerOptions = [
  { label: '不限', value: 0 },
  { label: '15分', value: 15 },
  { label: '30分', value: 30 },
  { label: '45分', value: 45 },
  { label: '播完即止', value: -1 },
]

function setSleepTimer(val) {
  sleepTimerMinutes.value = val
  if (sleepTimerInterval) {
    clearInterval(sleepTimerInterval)
    sleepTimerInterval = null
  }
  if (val > 0) {
    sleepTimerRemaining.value = val * 60
    sleepTimerInterval = setInterval(() => {
      sleepTimerRemaining.value--
      if (sleepTimerRemaining.value === 8) {
        fadeOutAndStop(8000)
      }
      if (sleepTimerRemaining.value <= 0) {
        clearInterval(sleepTimerInterval)
        sleepTimerInterval = null
        sleepTimerMinutes.value = 0
      }
    }, 1000)
  } else {
    sleepTimerRemaining.value = 0
  }
}

const remainingTimerFormatted = computed(() => {
  if (sleepTimerMinutes.value === -1) return '播完本品即停'
  if (sleepTimerRemaining.value <= 0) return ''
  const m = Math.floor(sleepTimerRemaining.value / 60)
  const s = sleepTimerRemaining.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

// --- 初始化 Audio Engine ---
const {
  currentTime,
  duration,
  isPlaying,
  currentParagraphId,
  progress,
  loadAudio,
  play,
  pause,
  toggle,
  seekByPercent,
  updateMediaSession,
  playNextTrack,
  switchVoiceTrack,
  fadeOutAndStop,
} = useAudioSync(paragraphsRef, {
  getPlayMode: () => playMode.value,
  onEnded: () => {
    if (sleepTimerMinutes.value === -1) {
      sleepTimerMinutes.value = 0
      return
    }
    if (playMode.value === 'sequence' && hasNextChapter.value) {
      goToNextChapter(true)
    }
  },
  onNext: () => goToNextChapter(),
  onPrev: () => goToPrevChapter()
})

// 无缝切男女声
function onVoiceChange(newVoice) {
  selectedVoice.value = newVoice
  localStorage.setItem('chanyue_voice', newVoice)
  const rawUrl = chapterData.value?.audioUrl || bookMeta.value?.audioUrl
  if (rawUrl) {
    const targetUrl = getVoiceAudioUrl(rawUrl, newVoice)
    switchVoiceTrack(targetUrl)
  }
}

// 格式化时间 mm:ss
function fmt(sec) {
  if (!sec || isNaN(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const timeDisplay = computed(() => `${fmt(currentTime.value)} / ${fmt(duration.value)}`)

// 辅助函数：提取标题字符串
function extractText(val) {
  if (!val) return ''
  if (typeof val === 'string') return val
  if (Array.isArray(val)) {
    return val.map(item => typeof item === 'object' ? item.text : item).join('')
  }
  return String(val)
}

// 当前经文段落高亮大字
const currentLineText = computed(() => {
  if (!chapterData.value?.paragraphs || chapterData.value.paragraphs.length === 0) {
    return '静心沉气 · 随音入定'
  }
  if (currentParagraphId.value !== -1) {
    const p = chapterData.value.paragraphs.find(item => item.id === currentParagraphId.value)
    if (p) {
      const rawText = extractText(p.content || p.text || p.words)
      if (rawText) return rawText
    }
  }
  // 默认显示首句或经题要语
  const firstP = chapterData.value.paragraphs[0]
  return extractText(firstP?.content || firstP?.text) || '静心沉气 · 随音入定'
})

// 章节索引与前后切品
const currentChapterIdx = computed(() => {
  return chaptersList.value.findIndex(ch => (ch.id || ch.chapterId) === selectedChapterId.value)
})

const hasPrevChapter = computed(() => currentChapterIdx.value > 0)
const hasNextChapter = computed(() => currentChapterIdx.value !== -1 && currentChapterIdx.value < chaptersList.value.length - 1)

function goToPrevChapter() {
  if (hasPrevChapter.value) {
    const target = chaptersList.value[currentChapterIdx.value - 1]
    changeChapter(target.id || target.chapterId)
  }
}

function goToNextChapter(autoPlayNext = false) {
  if (hasNextChapter.value) {
    const target = chaptersList.value[currentChapterIdx.value + 1]
    changeChapter(target.id || target.chapterId, autoPlayNext)
  }
}

// 切换经书
async function switchBook(bookId) {
  if (selectedBookId.value === bookId) return
  selectedBookId.value = bookId
  selectedChapterId.value = 'chapter_1'
  localStorage.setItem('chanyue_listen_book', bookId)
  localStorage.setItem('chanyue_listen_chapter', 'chapter_1')
  await loadBookMeta()
  await loadChapterData(false)
}

// 切换章节
async function changeChapter(chId, autoPlay = false) {
  selectedChapterId.value = chId
  localStorage.setItem('chanyue_listen_chapter', chId)
  await loadChapterData(autoPlay)
}

// 加载图书元数据
async function loadBookMeta() {
  try {
    const metaMod = await import(`../data/${selectedBookId.value}/index.json`)
    bookMeta.value = metaMod.default || metaMod
  } catch (e) {
    console.error('Failed to load book meta', e)
  }
}

// 加载章节数据
async function loadChapterData(autoPlay = false) {
  isLoading.value = true
  try {
    const chMod = await import(`../data/${selectedBookId.value}/${selectedChapterId.value}.json`)
    chapterData.value = chMod.default || chMod

    const rawUrl = chapterData.value.audioUrl || bookMeta.value?.audioUrl
    const audioUrl = getVoiceAudioUrl(rawUrl, selectedVoice.value)

    if (audioUrl) {
      if (autoPlay) {
        playNextTrack(audioUrl)
      } else {
        loadAudio(audioUrl)
      }
    }

    updateMediaSession({
      title: extractText(chapterData.value?.title),
      artist: extractText(bookMeta.value?.title),
      album: '禅阅 · 禅听台'
    })
  } catch (e) {
    console.error('Failed to load chapter in ZenAudioStation', e)
  } finally {
    isLoading.value = false
  }
}

// 进度条点击
function onProgressClick(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  seekByPercent(Math.max(0, Math.min(100, pct)))
}

// 跳转至经文全文阅读
function goToReader() {
  router.push(`/${selectedBookId.value}/${selectedChapterId.value}`)
}

onMounted(async () => {
  await loadBookMeta()
  await loadChapterData(false)
})

onUnmounted(() => {
  if (sleepTimerInterval) clearInterval(sleepTimerInterval)
})
</script>

<template>
  <div class="zen-station-wrapper">
    <!-- 顶部典籍切选药丸 -->
    <div class="sutra-selector">
      <button
        v-for="item in catalog"
        :key="item.id"
        class="sutra-chip"
        :class="{ active: selectedBookId === item.id }"
        @click="switchBook(item.id)"
      >
        <span class="chip-ornament">◈</span>
        <span>{{ item.id === 'xinjing' ? '心经' : '金刚经' }}</span>
      </button>
    </div>

    <!-- 品目微选择（若是金刚经等多品经典，呈现清雅横滑/选择） -->
    <div v-if="chaptersList.length > 1" class="chapter-scroll-bar">
      <button
        v-for="(ch, idx) in chaptersList"
        :key="ch.id || ch.chapterId"
        class="ch-pill"
        :class="{ active: (ch.id || ch.chapterId) === selectedChapterId }"
        @click="changeChapter(ch.id || ch.chapterId)"
      >
        <span class="ch-idx">{{ String(idx + 1).padStart(2, '0') }}</span>
        <span>{{ ch.title }}</span>
      </button>
    </div>

    <!-- 核心闭目大字沉浸视界 -->
    <section class="zen-focus-box">
      <div class="zen-title-wrap">
        <span class="zen-ornament">◈</span>
        <h2 class="zen-book-title">{{ extractText(bookMeta?.title) }}</h2>
        <p v-if="chaptersList.length > 1" class="zen-chapter-title">
          {{ extractText(chapterData?.title) }}
        </p>
      </div>

      <!-- 当前念诵经句微光呼吸 -->
      <div class="zen-verse-card" :class="{ 'is-playing': isPlaying }">
        <p class="verse-text">
          “{{ currentLineText }}”
        </p>
      </div>
    </section>

    <!-- 进阶修持三大控制区（舒展宽裕，互不挤占） -->
    <div class="zen-deck">
      <!-- 控制行 1：持诵流转模式 -->
      <div class="deck-row">
        <span class="row-label">持诵流转</span>
        <div class="row-buttons">
          <button 
            class="deck-chip" 
            :class="{ active: playMode === 'sequence' }"
            @click="playMode = 'sequence'"
          >
            连播全卷
          </button>
          <button 
            class="deck-chip" 
            :class="{ active: playMode === 'single' }"
            @click="playMode = 'single'"
          >
            单品听诵
          </button>
          <button 
            class="deck-chip" 
            :class="{ active: playMode === 'repeat-one' }"
            @click="playMode = 'repeat-one'"
          >
            循环持诵
          </button>
        </div>
      </div>

      <!-- 控制行 2：禅修/睡前定时 -->
      <div class="deck-row">
        <div class="row-label-wrap">
          <span class="row-label">禅修定时</span>
          <span v-if="remainingTimerFormatted" class="timer-countdown">⏳ {{ remainingTimerFormatted }}</span>
        </div>
        <div class="row-buttons">
          <button
            v-for="opt in timerOptions"
            :key="opt.value"
            class="deck-chip"
            :class="{ active: sleepTimerMinutes === opt.value }"
            @click="setSleepTimer(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 控制行 3：双法音声线切换 -->
      <div class="deck-row">
        <span class="row-label">持诵法音</span>
        <div class="row-buttons">
          <button 
            class="deck-chip" 
            :class="{ active: selectedVoice === 'female' }"
            @click="onVoiceChange('female')"
          >
            清平女声 · 莲华
          </button>
          <button 
            class="deck-chip" 
            :class="{ active: selectedVoice === 'male' }"
            @click="onVoiceChange('male')"
          >
            沉稳男声 · 暮钟
          </button>
        </div>
      </div>

      <!-- 进度条区 -->
      <div class="zen-progress-section">
        <div class="progress-track-wrap" @click="onProgressClick">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
            <div class="progress-thumb" :style="{ left: `${progress}%` }"></div>
          </div>
        </div>
        <div class="progress-meta">
          <span>{{ fmt(currentTime) }}</span>
          <span>{{ fmt(duration) }}</span>
        </div>
      </div>

      <!-- 主控制轮盘（大号播放键 + 上下品切换） -->
      <div class="zen-master-controls">
        <button 
          class="step-btn" 
          :disabled="!hasPrevChapter" 
          @click="goToPrevChapter()"
          title="上一品"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path d="M19 20L9 12l10-8v16zM5 19V5"/>
          </svg>
        </button>

        <button 
          class="master-play-btn" 
          :class="{ playing: isPlaying }"
          @click="toggle"
          :title="isPlaying ? '暂停听诵' : '开始听诵'"
        >
          <svg v-if="!isPlaying" viewBox="0 0 24 24" fill="currentColor" width="28" height="28" style="margin-left: 2px;">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
            <rect x="6" y="4" width="4" height="16" rx="1"/>
            <rect x="14" y="4" width="4" height="16" rx="1"/>
          </svg>
        </button>

        <button 
          class="step-btn" 
          :disabled="!hasNextChapter" 
          @click="goToNextChapter()"
          title="下一品"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path d="M5 4l10 8-10 8V4zM19 5v14"/>
          </svg>
        </button>
      </div>

      <!-- 直通全文精读轻链 -->
      <div class="reader-portal-link" @click="goToReader">
        <span>前往阅读本卷全文</span>
        <span class="portal-arrow">→</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.zen-station-wrapper {
  animation: fadeIn 0.8s ease both;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 顶部经卷切换药丸 */
.sutra-selector {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.sutra-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 18px;
  border-radius: 9999px;
  background: rgba(22, 22, 28, 0.7);
  border: 1px solid rgba(212, 165, 116, 0.2);
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.sutra-chip:hover {
  border-color: rgba(212, 165, 116, 0.45);
  color: var(--text-primary);
}

.sutra-chip.active {
  background: rgba(212, 165, 116, 0.16);
  border-color: rgba(212, 165, 116, 0.65);
  color: var(--gold);
  font-weight: 600;
  box-shadow: 0 0 16px rgba(212, 165, 116, 0.15);
}

.chip-ornament {
  font-size: 10px;
  opacity: 0.6;
}

/* 章节横滑条（针对金刚经等长篇） */
.chapter-scroll-bar {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 4px 10px;
  scrollbar-width: none;
  -ms-overflow-style: none;
  scroll-behavior: smooth;
}

.chapter-scroll-bar::-webkit-scrollbar {
  display: none;
}

.ch-pill {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 9999px;
  background: rgba(26, 26, 34, 0.6);
  border: 1px solid rgba(212, 165, 116, 0.15);
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ch-pill:hover {
  color: var(--text-primary);
  border-color: rgba(212, 165, 116, 0.35);
}

.ch-pill.active {
  background: rgba(212, 165, 116, 0.2);
  border-color: rgba(212, 165, 116, 0.6);
  color: var(--gold);
}

.ch-idx {
  font-family: monospace;
  font-size: 10px;
  opacity: 0.7;
}

/* 沉浸大字闭目视界 */
.zen-focus-box {
  text-align: center;
  padding: 18px 12px 10px;
}

.zen-title-wrap {
  margin-bottom: 20px;
}

.zen-ornament {
  font-size: 14px;
  color: var(--gold);
  opacity: 0.5;
  letter-spacing: 6px;
  display: block;
  margin-bottom: 4px;
}

.zen-book-title {
  margin: 0 0 6px;
  font-size: 21px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-primary);
  letter-spacing: 4px;
  font-weight: 700;
}

.zen-chapter-title {
  margin: 0;
  font-size: 13.5px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--gold-dim);
  letter-spacing: 2px;
}

.zen-verse-card {
  padding: 24px 20px;
  background: rgba(22, 22, 30, 0.45);
  border: 1px solid rgba(212, 165, 116, 0.14);
  border-radius: 16px;
  min-height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 24px rgba(0, 0, 0, 0.4);
  transition: all 0.5s ease;
}

.zen-verse-card.is-playing {
  border-color: rgba(212, 165, 116, 0.32);
  background: rgba(28, 28, 38, 0.6);
  box-shadow: 0 0 28px rgba(212, 165, 116, 0.08), inset 0 0 32px rgba(212, 165, 116, 0.04);
}

.verse-text {
  margin: 0;
  font-size: 15.5px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-primary);
  line-height: 1.85;
  letter-spacing: 2px;
  text-align: center;
  transition: all 0.35s ease;
}

.zen-verse-card.is-playing .verse-text {
  color: var(--gold);
  text-shadow: 0 0 16px rgba(212, 165, 116, 0.35);
}

/* 控制台底板 */
.zen-deck {
  background: rgba(18, 18, 26, 0.7);
  border: 1px solid rgba(212, 165, 116, 0.16);
  border-radius: 20px;
  padding: 20px 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  backdrop-filter: blur(16px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
}

.deck-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deck-row .row-label-wrap,
.deck-row .row-label {
  font-size: 12px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-muted);
  letter-spacing: 1.5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timer-countdown {
  font-family: monospace;
  font-size: 11.5px;
  color: var(--gold);
}

.row-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.deck-chip {
  background: rgba(212, 165, 116, 0.05);
  border: 1px solid rgba(212, 165, 116, 0.16);
  border-radius: 9999px;
  padding: 4px 12px;
  font-size: 12px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}

.deck-chip:hover {
  border-color: rgba(212, 165, 116, 0.35);
  color: var(--text-primary);
}

.deck-chip.active {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.6);
  color: var(--gold);
  font-weight: 600;
}

/* 进度条 */
.zen-progress-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.progress-track-wrap {
  padding: 8px 0;
  cursor: pointer;
}

.progress-track {
  height: 4px;
  background: rgba(212, 165, 116, 0.16);
  border-radius: 9999px;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(212, 165, 116, 0.7), var(--gold));
  border-radius: 9999px;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--gold);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 8px rgba(212, 165, 116, 0.6);
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-family: monospace;
  color: var(--text-muted);
}

/* 主控制器 */
.zen-master-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 6px;
}

.step-btn {
  background: none;
  border: 1px solid rgba(212, 165, 116, 0.2);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.step-btn:hover:not(:disabled) {
  border-color: rgba(212, 165, 116, 0.5);
  color: var(--gold);
  transform: scale(1.05);
}

.step-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.master-play-btn {
  width: 62px;
  height: 62px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.25), rgba(212, 165, 116, 0.1));
  border: 1.5px solid rgba(212, 165, 116, 0.55);
  color: var(--gold);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(212, 165, 116, 0.2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.master-play-btn:hover {
  transform: scale(1.08);
  border-color: var(--gold);
  box-shadow: 0 0 28px rgba(212, 165, 116, 0.4);
}

.master-play-btn.playing {
  animation: pulseGlow 3s infinite alternate ease-in-out;
}

@keyframes pulseGlow {
  0% { box-shadow: 0 0 16px rgba(212, 165, 116, 0.2); }
  100% { box-shadow: 0 0 32px rgba(212, 165, 116, 0.45); }
}

/* 前往阅读链接 */
.reader-portal-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
  color: var(--gold-dim);
  font-family: 'Noto Serif SC', serif;
  font-size: 12.5px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reader-portal-link:hover {
  color: var(--gold);
  transform: translateX(2px);
}

.portal-arrow {
  transition: transform 0.2s ease;
}

.reader-portal-link:hover .portal-arrow {
  transform: translateX(3px);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
