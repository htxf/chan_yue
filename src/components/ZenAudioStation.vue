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

// 弹窗状态
const isChapterDrawerOpen = ref(false)
const isTimerModalOpen = ref(false)

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

function cyclePlayMode() {
  const isMulti = chaptersList.value.length > 1
  const modes = isMulti ? ['sequence', 'single', 'repeat-one'] : ['single', 'repeat-one']
  const idx = modes.indexOf(playMode.value)
  playMode.value = modes[(idx + 1) % modes.length]
}

const playModeLabel = computed(() => {
  if (playMode.value === 'repeat-one') return '循环持诵'
  if (playMode.value === 'single') return '单品听诵'
  return chaptersList.value.length > 1 ? '连播全卷' : '单品听诵'
})

// 禅修定时 (分钟): 0(不限), 15, 30, 45, 60, -1(播完本品)
const sleepTimerMinutes = ref(0)
const sleepTimerRemaining = ref(0)
let sleepTimerInterval = null

const timerOptions = [
  { label: '不限定时', value: 0 },
  { label: '15 分钟', value: 15 },
  { label: '30 分钟', value: 30 },
  { label: '45 分钟', value: 45 },
  { label: '60 分钟', value: 60 },
  { label: '播完本品即止', value: -1 },
]

function selectTimerOption(val) {
  setSleepTimer(val)
  isTimerModalOpen.value = false
}

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

const timerSummaryText = computed(() => {
  if (sleepTimerMinutes.value === -1) return '播完即止'
  if (sleepTimerRemaining.value > 0) {
    const m = Math.floor(sleepTimerRemaining.value / 60)
    const s = sleepTimerRemaining.value % 60
    return `⏳ ${m}:${s.toString().padStart(2, '0')}`
  }
  return '禅修定时'
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

// 辅助函数：提取标题字符串
function extractText(val) {
  if (!val) return ''
  if (typeof val === 'string') return val
  if (Array.isArray(val)) {
    return val.map(item => typeof item === 'object' ? item.text : item).join('')
  }
  return String(val)
}

// 章节索引与前后切品
const currentChapterIdx = computed(() => {
  return chaptersList.value.findIndex(ch => (ch.id || ch.chapterId) === selectedChapterId.value)
})

const hasPrevChapter = computed(() => currentChapterIdx.value > 0)
const hasNextChapter = computed(() => currentChapterIdx.value !== -1 && currentChapterIdx.value < chaptersList.value.length - 1)

function goToPrevChapter() {
  if (hasPrevChapter.value) {
    const target = chaptersList.value[currentChapterIdx.value - 1]
    changeChapter(target.id || target.chapterId, isPlaying.value)
  }
}

function goToNextChapter(autoPlayNext = false) {
  if (hasNextChapter.value) {
    const target = chaptersList.value[currentChapterIdx.value + 1]
    changeChapter(target.id || target.chapterId, autoPlayNext || isPlaying.value)
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
  if (chaptersList.value.length <= 1 && playMode.value === 'sequence') {
    playMode.value = 'single'
  }
  await loadChapterData(false)
}

// 切换章节
async function changeChapter(chId, autoPlay = false) {
  selectedChapterId.value = chId
  localStorage.setItem('chanyue_listen_chapter', chId)
  isChapterDrawerOpen.value = false
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
  <div class="zen-station-viewport">
    <!-- 顶部：沉静典雅的经题微印章（点击可纵向自如挑选经卷与品目，无臃肿横向小滑块） -->
    <div class="sutra-header-bar" @click="isChapterDrawerOpen = true">
      <div class="sutra-select-pill">
        <span class="pill-ornament">◈</span>
        <span class="pill-title">{{ extractText(bookMeta?.title) }}</span>
        <span v-if="chaptersList.length > 1" class="pill-divider">·</span>
        <span v-if="chaptersList.length > 1" class="pill-chapter">{{ extractText(chapterData?.title) }}</span>
        <svg class="pill-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </div>
    </div>

    <!-- 中腹：空灵沉静的大字闭目视界（大字经名与品目，无乱码，无多余占位短语） -->
    <section class="zen-sacred-center">
      <div class="sacred-seal">◈</div>
      <h2 class="sacred-book-title">{{ extractText(bookMeta?.title) }}</h2>
      <p class="sacred-chapter-title">
        {{ chaptersList.length > 1 ? extractText(chapterData?.title) : (extractText(bookMeta?.author) || '唐·玄奘法师译') }}
      </p>
    </section>

    <!-- 底部：专业随身听底座（保留手感极佳的大播放键组，上方融入极简调谐一行） -->
    <div class="zen-player-deck">
      <!-- 极简器物微调谐栏（只占单行，告别表单堆叠） -->
      <div class="tuning-bar">
        <!-- 循环模式切选 -->
        <button 
          class="tune-btn" 
          :class="{ active: playMode === 'repeat-one' }" 
          @click="cyclePlayMode"
          title="切换持诵流转模式"
        >
          <svg v-if="playMode === 'sequence'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <path d="M17 2l4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>
          </svg>
          <svg v-else-if="playMode === 'single'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <path d="M5 12h13M13 6l6 6-6 6"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <path d="M17 2l4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>
            <circle cx="12" cy="12" r="1.8" fill="currentColor"/>
          </svg>
          <span>{{ playModeLabel }}</span>
        </button>

        <span class="tune-sep">·</span>

        <!-- 音色无缝接续切换 -->
        <button 
          class="tune-btn" 
          @click="onVoiceChange(selectedVoice === 'female' ? 'male' : 'female')"
          title="切换持诵法音"
        >
          <svg v-if="selectedVoice === 'female'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <path d="M12 3a9 9 0 0 0-9 9c0 4.97 4.03 9 9 9s9-4.03 9-9a9 9 0 0 0-9-9z" opacity="0.3"/>
            <path d="M12 7c-2 2.5-3 5-3 7a3 3 0 0 0 6 0c0-2-1-4.5-3-7z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <path d="M4 20h16M6 20v-7a6 6 0 0 1 12 0v7M12 4v3"/>
          </svg>
          <span>{{ selectedVoice === 'female' ? '莲华女声' : '暮钟男声' }}</span>
        </button>

        <span class="tune-sep">·</span>

        <!-- 禅修定时设定 -->
        <button 
          class="tune-btn" 
          :class="{ active: sleepTimerMinutes !== 0 }" 
          @click="isTimerModalOpen = true"
          title="设定禅修定时"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="12" height="12">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          <span>{{ timerSummaryText }}</span>
        </button>
      </div>

      <!-- 进度条区（舒展宽裕） -->
      <div class="progress-section">
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

      <!-- 用户喜爱的大播放键控制台（原汁原味保留尺寸、手感与呼吸动画） -->
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

    <!-- 弹窗一：经卷与品目选择抽屉（竖向纵列 32 品，纵向滑动自如，无限扩展） -->
    <transition name="drawer-fade">
      <div v-if="isChapterDrawerOpen" class="modal-overlay" @click.self="isChapterDrawerOpen = false">
        <div class="modal-sheet">
          <div class="sheet-header">
            <div class="sheet-title-box">
              <h3>经 卷 选 择</h3>
              <p>请点选经典与品目</p>
            </div>
            <button class="sheet-close" @click="isChapterDrawerOpen = false">×</button>
          </div>

          <!-- 经书切换标签 -->
          <div class="sheet-book-tabs">
            <button 
              v-for="item in catalog" 
              :key="item.id" 
              class="book-tab-btn" 
              :class="{ active: selectedBookId === item.id }"
              @click="switchBook(item.id)"
            >
              {{ item.id === 'xinjing' ? '心经' : '金刚经' }}
            </button>
          </div>

          <!-- 纵向品目列表 -->
          <div class="sheet-chapter-list">
            <div 
              v-for="(ch, idx) in chaptersList" 
              :key="ch.id || ch.chapterId"
              class="sheet-ch-item"
              :class="{ active: (ch.id || ch.chapterId) === selectedChapterId }"
              @click="changeChapter(ch.id || ch.chapterId, isPlaying)"
            >
              <div class="ch-meta">
                <span class="ch-idx-num">{{ String(idx + 1).padStart(2, '0') }}</span>
                <span class="ch-name">{{ ch.title }}</span>
              </div>
              <span v-if="(ch.id || ch.chapterId) === selectedChapterId" class="ch-playing-badge">当前诵读</span>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 弹窗二：禅修定时轻雅气泡（单点即定，无需繁琐键盘输入） -->
    <transition name="drawer-fade">
      <div v-if="isTimerModalOpen" class="modal-overlay" @click.self="isTimerModalOpen = false">
        <div class="timer-sheet">
          <div class="timer-sheet-header">
            <span class="sheet-ornament">◈</span>
            <h4>禅 修 定 时</h4>
            <p>定时停止前 8 秒音量平滑渐弱淡出</p>
          </div>

          <div class="timer-option-grid">
            <button
              v-for="opt in timerOptions"
              :key="opt.value"
              class="timer-opt-chip"
              :class="{ active: sleepTimerMinutes === opt.value }"
              @click="selectTimerOption(opt.value)"
            >
              <span>{{ opt.label }}</span>
            </button>
          </div>

          <button class="timer-sheet-cancel" @click="isTimerModalOpen = false">取消</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* 一屏沉浸容器：彻底消灭向下滚动 */
.zen-station-viewport {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: calc(100vh - 190px);
  gap: 16px;
  animation: fadeIn 0.6s ease both;
}

/* 顶部：经题印章选择器 */
.sutra-header-bar {
  display: flex;
  justify-content: center;
  margin-top: 4px;
}

.sutra-select-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 16px;
  border-radius: 9999px;
  background: rgba(22, 22, 30, 0.65);
  border: 1px solid rgba(212, 165, 116, 0.22);
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 1.5px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: all 0.25s ease;
  max-width: 92%;
}

.sutra-select-pill:hover {
  border-color: rgba(212, 165, 116, 0.5);
  background: rgba(212, 165, 116, 0.1);
  transform: translateY(-1px);
}

.pill-ornament {
  color: var(--gold);
  font-size: 11px;
}

.pill-title {
  font-weight: 600;
  color: var(--gold);
  white-space: nowrap;
}

.pill-divider {
  color: rgba(212, 165, 116, 0.4);
}

.pill-chapter {
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pill-arrow {
  color: var(--gold);
  opacity: 0.7;
  flex-shrink: 0;
  margin-left: 2px;
}

/* 中腹：空生万物的神圣留白大字 */
.zen-sacred-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px 12px;
  min-height: 180px;
}

.sacred-seal {
  font-size: 14px;
  color: var(--gold);
  opacity: 0.5;
  letter-spacing: 6px;
  margin-bottom: 6px;
}

.sacred-book-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-primary);
  letter-spacing: 6px;
  font-weight: 700;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.8);
}

.sacred-chapter-title {
  margin: 0 0 20px;
  font-size: 14px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--gold-dim);
  letter-spacing: 2px;
}

.sacred-verse-glow {
  max-width: 480px;
  padding: 8px 16px;
  transition: all 0.5s ease;
}

.sacred-verse-text {
  margin: 0;
  font-size: 16px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  line-height: 1.85;
  letter-spacing: 2px;
  transition: all 0.35s ease;
}

.sacred-verse-glow.is-playing .sacred-verse-text {
  color: var(--gold);
  text-shadow: 0 0 20px rgba(212, 165, 116, 0.45);
}

/* 底部：专业随身听底座 */
.zen-player-deck {
  background: rgba(18, 18, 26, 0.75);
  border: 1px solid rgba(212, 165, 116, 0.18);
  border-radius: 22px;
  padding: 16px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  backdrop-filter: blur(20px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}

/* 极简调谐一行 */
.tuning-bar {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 4px 6px 6px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.1);
}

.tune-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  letter-spacing: 1.2px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.tune-btn:hover {
  color: var(--text-primary);
}

.tune-btn.active {
  color: var(--gold);
  font-weight: 600;
}

.tune-sep {
  color: rgba(212, 165, 116, 0.25);
  font-size: 12px;
}

/* 进度条 */
.progress-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-track-wrap {
  padding: 6px 0;
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
  font-size: 10.5px;
  font-family: monospace;
  color: var(--text-muted);
}

/* 主控制器 */
.zen-master-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 26px;
}

.step-btn {
  background: none;
  border: 1px solid rgba(212, 165, 116, 0.2);
  width: 42px;
  height: 42px;
  border-radius: 50%;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.step-btn:hover:not(:disabled) {
  border-color: rgba(212, 165, 116, 0.55);
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
  color: var(--gold-dim);
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
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

/* 模态遮罩 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px);
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

/* 经卷选择抽屉 */
.modal-sheet {
  background: rgba(18, 18, 26, 0.95);
  border-top: 1px solid rgba(212, 165, 116, 0.25);
  border-radius: 24px 24px 0 0;
  width: 100%;
  max-width: 580px;
  max-height: 75vh;
  display: flex;
  flex-direction: column;
  padding: 20px 20px 32px;
  box-shadow: 0 -12px 40px rgba(0, 0, 0, 0.8);
}

.sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.12);
}

.sheet-title-box h3 {
  margin: 0 0 2px;
  font-size: 17px;
  font-family: 'Noto Serif SC', serif;
  color: var(--gold);
  letter-spacing: 3px;
}

.sheet-title-box p {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-muted);
}

.sheet-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 26px;
  cursor: pointer;
  line-height: 1;
}

.sheet-book-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.book-tab-btn {
  flex: 1;
  padding: 8px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.2);
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.book-tab-btn.active {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.6);
  color: var(--gold);
  font-weight: 600;
}

.sheet-chapter-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 4px;
}

.sheet-ch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sheet-ch-item:hover {
  background: rgba(212, 165, 116, 0.08);
}

.sheet-ch-item.active {
  background: rgba(212, 165, 116, 0.14);
}

.ch-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ch-idx-num {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-muted);
  width: 22px;
}

.sheet-ch-item.active .ch-idx-num {
  color: var(--gold);
  font-weight: bold;
}

.ch-name {
  font-family: 'Noto Serif SC', serif;
  font-size: 13.5px;
  color: var(--text-primary);
}

.sheet-ch-item.active .ch-name {
  color: var(--gold);
  font-weight: 600;
}

.ch-playing-badge {
  font-size: 11px;
  font-family: 'Noto Serif SC', serif;
  color: var(--gold);
  background: rgba(212, 165, 116, 0.12);
  padding: 2px 8px;
  border-radius: 9999px;
  border: 1px solid rgba(212, 165, 116, 0.3);
}

/* 定时气泡小面板 */
.timer-sheet {
  background: rgba(18, 18, 26, 0.96);
  border: 1px solid rgba(212, 165, 116, 0.3);
  border-radius: 20px;
  width: calc(100% - 32px);
  max-width: 440px;
  margin-bottom: 24px;
  padding: 24px 20px;
  text-align: center;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.8);
}

.timer-sheet-header {
  margin-bottom: 18px;
}

.sheet-ornament {
  font-size: 13px;
  color: var(--gold);
  opacity: 0.6;
}

.timer-sheet-header h4 {
  margin: 4px 0;
  font-size: 17px;
  font-family: 'Noto Serif SC', serif;
  color: var(--gold);
  letter-spacing: 3px;
}

.timer-sheet-header p {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-muted);
}

.timer-option-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.timer-opt-chip {
  padding: 10px 16px;
  border-radius: 12px;
  background: rgba(212, 165, 116, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.18);
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.timer-opt-chip:hover {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.12);
}

.timer-opt-chip.active {
  background: rgba(212, 165, 116, 0.22);
  border-color: rgba(212, 165, 116, 0.65);
  color: var(--gold);
  font-weight: 600;
}

.timer-sheet-cancel {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  font-family: 'Noto Serif SC', serif;
  cursor: pointer;
  padding: 6px;
}

.timer-sheet-cancel:hover {
  color: var(--text-primary);
}

/* 过渡动效 */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.25s ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
