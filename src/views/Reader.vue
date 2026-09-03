<script setup>
import { ref, onMounted, onUnmounted, watch, shallowRef, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SutraHeader from '../components/SutraHeader.vue'
import ModeSelector from '../components/ModeSelector.vue'
import SutraBody from '../components/SutraBody.vue'
import AudioPlayer from '../components/AudioPlayer.vue'
import { useAudioSync } from '../composables/useAudioSync.js'

const route = useRoute()
const router = useRouter()

const bookMeta = shallowRef(null)
const chapterData = shallowRef(null)
const mode = ref(route.query.mode || 'reading')
const showDrawer = ref(false)
const isLoading = ref(true)
const isZenMode = ref(false)

function extractText(val) {
  if (!val) return ''
  if (typeof val === 'string') return val
  if (Array.isArray(val)) {
    return val.map(item => typeof item === 'object' ? item.text : item).join('')
  }
  return String(val)
}

const bookId = computed(() => route.params.bookId)
const chapterId = computed(() => route.params.chapterId || 'chapter_1')

const autoPlayNext = ref(localStorage.getItem('chanyue_autoplay') !== 'false')
watch(autoPlayNext, (val) => {
  localStorage.setItem('chanyue_autoplay', val)
})

let autoPlayTimer = null

const paragraphsRef = computed(() => chapterData.value?.paragraphs || [])

const selectedVoice = ref(localStorage.getItem('chanyue_voice') || 'female')

function getVoiceAudioUrl(rawUrl, voice = selectedVoice.value) {
  if (!rawUrl) return rawUrl
  if (rawUrl.endsWith('.mp3')) {
    const base = rawUrl.slice(0, -4).replace(/_(female|male)$/, '')
    return `${base}_${voice}.mp3`
  }
  return rawUrl
}

function onVoiceChange(newVoice) {
  selectedVoice.value = newVoice
  localStorage.setItem('chanyue_voice', newVoice)
  const rawUrl = chapterData.value?.audioUrl || bookMeta.value?.audioUrl
  if (rawUrl) {
    const targetUrl = getVoiceAudioUrl(rawUrl, newVoice)
    const wasPlaying = isPlaying.value
    const prevPct = progress.value
    loadAudio(targetUrl)
    if (wasPlaying) {
      setTimeout(() => {
        seekByPercent(prevPct)
        play()
      }, 150)
    }
  }
}

const {
  currentTime,
  duration,
  isPlaying,
  currentParagraphId,
  progress,
  loadAudio,
  play,
  toggle,
  pause,
  seekByPercent,
  updateMediaSession,
  playNextTrack,
} = useAudioSync(paragraphsRef, {
  onEnded: () => {
    if (autoPlayNext.value && nextChapter.value) {
      const nextId = nextChapter.value.id || nextChapter.value.chapterId
      const audioUrl = getVoiceAudioUrl(`/audio/${bookId.value}/${nextId}.mp3`, selectedVoice.value)
      // 零延迟同步接力：在同一个同步栈内切 src + play()
      // 让 OS 保持音频焦点不释放
      playNextTrack(audioUrl)
      // 路由和数据加载异步跟进，不阻塞音频
      goToNextChapter(true)
    }
  },
  onNext: () => goToNextChapter(),
  onPrev: () => goToPrevChapter()
})

const isTopbarHidden = ref(false)
let lastScrollY = 0

function handleWindowScroll() {
  const currentY = window.scrollY
  if (currentY > 120 && currentY > lastScrollY + 15) {
    isTopbarHidden.value = true
  } else if (currentY < lastScrollY - 15 || currentY < 80) {
    isTopbarHidden.value = false
  }
  lastScrollY = currentY
}

onMounted(() => {
  window.addEventListener('scroll', handleWindowScroll, { passive: true })
})

onUnmounted(() => {
  if (autoPlayTimer) clearTimeout(autoPlayTimer)
  window.removeEventListener('scroll', handleWindowScroll)
})

// --- Interaction & UI Hide Logic ---
function goBack() {
  router.push('/')
}

function toggleDrawer() {
  showDrawer.value = !showDrawer.value
}

function selectChapter(id) {
  showDrawer.value = false
  router.push({ path: `/${bookId.value}/${id}`, query: { mode: mode.value } })
}

const prevChapter = computed(() => {
  if (!bookMeta.value || !bookMeta.value.chapters) return null
  const chapters = bookMeta.value.chapters
  const currentIndex = chapters.findIndex(c => (c.id || c.chapterId) === chapterId.value)
  if (currentIndex > 0) return chapters[currentIndex - 1]
  return null
})

const nextChapter = computed(() => {
  if (!bookMeta.value || !bookMeta.value.chapters) return null
  const chapters = bookMeta.value.chapters
  const currentIndex = chapters.findIndex(c => (c.id || c.chapterId) === chapterId.value)
  if (currentIndex >= 0 && currentIndex < chapters.length - 1) return chapters[currentIndex + 1]
  return null
})

let isAutoPlayingNext = false

function goToNextChapter(isAutoPlay = false) {
  if (nextChapter.value) {
    if (isAutoPlay) isAutoPlayingNext = true
    selectChapter(nextChapter.value.id || nextChapter.value.chapterId)
  }
}

function goToPrevChapter() {
  if (prevChapter.value) {
    selectChapter(prevChapter.value.id || prevChapter.value.chapterId)
  }
}

watch([bookId, chapterId], async ([newBookId, newChapterId], [oldBookId, oldChapterId]) => {
  if (newBookId !== oldBookId) {
    await loadBookData()
  }
  if (newChapterId !== oldChapterId || newBookId !== oldBookId) {
    await loadChapterData()
  }
})

// --- Data Loading ---
async function loadBookData() {
  try {
    const metaModule = await import(`../data/${bookId.value}/index.json`)
    bookMeta.value = metaModule.default || metaModule
  } catch (err) {
    console.error('Failed to load book metadata', err)
    router.push('/')
  }
}

async function loadChapterData() {
  isLoading.value = true
  
  // 只有当这是『切章』（原本已经有数据了）时，才等待 350ms 播完淡出动画。
  // 如果是『首次从首页进入』，不需要等，直接去拉数据。
  // 注意：连播模式下不暂停——音频已经在 playNextTrack 中同步切换了
  if (chapterData.value) {
    await new Promise(resolve => setTimeout(resolve, 350))
    if (!isAutoPlayingNext) {
      pause()
    }
  }

  try {
    const chId = chapterId.value
    const dataModule = await import(`../data/${bookId.value}/${chId}.json`)
    chapterData.value = dataModule.default || dataModule
    
    // Update Media Session API Metadata
    updateMediaSession({
      title: extractText(chapterData.value?.title),
      artist: extractText(bookMeta.value?.title),
      album: '禅阅'
    })
    
    // Check if the current book has a global audioUrl or chapter-specific
    // Prefer chapter specific audio, fallback to book audio
    const rawAudioUrl = chapterData.value.audioUrl || bookMeta.value?.audioUrl
    const audioUrl = getVoiceAudioUrl(rawAudioUrl)
    if (audioUrl) {
      // 连播模式下 loadAudio 不会覆盖已经在播的 src（因为 URL 已经一致）
      loadAudio(audioUrl)
      // 非连播的正常进入 listening 模式时，延迟播放等 DOM 就绪
      if (mode.value === 'listening' && !isAutoPlayingNext) {
        setTimeout(() => play(), 600)
      }
    } else {
      if (!isAutoPlayingNext) pause()
      mode.value = 'reading'
    }
    isAutoPlayingNext = false // Reset the flag
    
    // 等待 Vue 渲染出新 DOM 的高度
    await nextTick()
    window.scrollTo({ top: 0 })

    // 记录最近一次持诵进度供首页“续读浮舟”一键直达
    try {
      localStorage.setItem('chanyue_last_read', JSON.stringify({
        bookId: bookId.value,
        chapterId: chId,
        chapterTitle: extractText(chapterData.value?.title),
        bookTitle: extractText(bookMeta.value?.title),
        time: Date.now()
      }))
    } catch (e) {}
  } catch (err) {
    console.error('Failed to load chapter data', err)
  } finally {
    // 使用双重 requestAnimationFrame 确保 CSS 动画引擎捕捉到状态变更
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        isLoading.value = false
      })
    })
  }
}

onMounted(async () => {
  await loadBookData()
  await loadChapterData()
})

/* 切换到阅读模式时暂停播放 */
watch(mode, (newMode) => {
  if (newMode === 'reading') {
    pause()
  }
})

/* 点击播放时，自动切换到禅听模式 */
function handleToggle() {
  if (mode.value === 'reading' && !isPlaying.value) {
    mode.value = 'listening'
  }
  toggle()
}

</script>

<template>
  <div class="reader-wrapper min-h-screen w-full bg-[var(--bg-primary)] pb-36 md:pb-32">
    
    <!-- Top Controls (自适应智能微缩浮动顶栏) -->
    <div 
      class="fixed top-3.5 left-4 right-4 md:top-5 md:left-6 md:right-6 z-[100] flex justify-between pointer-events-none transition-all duration-500 ease-out"
      :class="[
        isLoading ? 'opacity-0' : '',
        isTopbarHidden ? 'opacity-20 hover:opacity-100 -translate-y-2' : 'opacity-100 translate-y-0'
      ]"
    >
      <button class="nav-top-btn" @click.stop="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="12" height="12" class="nav-btn-icon">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
        <span class="nav-btn-text">返回书阁</span>
      </button>

      <button v-if="bookMeta && bookMeta.chapters && bookMeta.chapters.length > 1" class="nav-top-btn" @click.stop="toggleDrawer">
        <span class="nav-btn-text">经卷目录</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="12" height="12" class="nav-btn-icon">
          <path d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>
    </div>

    <!-- Chapter Drawer (器物级经卷目录抽屉) -->
    <transition name="slide-right">
      <div v-if="showDrawer" class="drawer-overlay" @click.stop="toggleDrawer">
        <div class="drawer-content" @click.stop>
          <div class="drawer-header">
            <div class="drawer-title-box">
              <h3>经卷目录</h3>
              <p class="drawer-subtitle">{{ extractText(bookMeta?.title) }} · 共 {{ bookMeta?.chapters?.length }} 品</p>
            </div>
            <button class="close-btn" @click="toggleDrawer">×</button>
          </div>
          <div class="drawer-body">
            <div 
              v-for="(chapter, idx) in bookMeta.chapters" 
              :key="chapter.id || chapter.chapterId"
              class="chapter-item"
              :class="{ active: (chapter.id || chapter.chapterId) === chapterId }"
              @click="selectChapter(chapter.id || chapter.chapterId)"
            >
              <div class="ch-left">
                <span class="ch-num">{{ String(idx + 1).padStart(2, '0') }}</span>
                <span class="ch-title">{{ chapter.title }}</span>
              </div>
              <span v-if="bookId === 'jingangjing' && idx < 8" class="badge-audio">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="10" height="10">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19 12a7 7 0 0 0-14 0" opacity="0.6"/>
                </svg>
                双音色
              </span>
              <span v-else class="badge-text">墨读</span>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <div 
      :class="isLoading ? 'opacity-0 scale-[0.99] blur-sm' : 'opacity-100 scale-100 blur-0'" 
      class="transition-all duration-500 ease-out flex flex-col"
      style="backface-visibility: hidden; transform: translateZ(0);"
    >
      <template v-if="bookMeta && chapterData">
        <!-- We only show header if it's the first chapter or if chapter has no title, but let's show the book title and chapter title -->
        <SutraHeader
          :title="bookMeta.title"
          :subtitle="chapterData.title"
          :author="bookMeta.author || chapterData.author"
          :isFirstChapter="chapterId === 'chapter_1' || !chapterId"
          :isMultiChapter="Boolean(bookMeta?.chapters && bookMeta.chapters.length > 1)"
          :isTitleActive="isPlaying && currentTime < (chapterData.paragraphs?.[0]?.startTime || 3.0)"
        />

        <ModeSelector v-model:mode="mode" />

        <SutraBody
          :paragraphs="chapterData.paragraphs"
          :currentParagraphId="currentParagraphId"
          :currentTime="currentTime"
          :mode="mode"
        >
          <template #footer>
            <div class="mt-24 mb-8 flex justify-between items-center text-gray-500 font-serif text-sm tracking-widest px-4 max-w-lg mx-auto">
              <button 
                v-if="prevChapter" 
                @click.stop="selectChapter(prevChapter.id || prevChapter.chapterId)"
                class="hover:text-amber-500 transition-colors duration-300 flex items-center gap-2"
              >
                <span>←</span> {{ prevChapter.title || '上一品' }}
              </button>
              <div v-else></div>

              <button 
                v-if="nextChapter" 
                @click.stop="selectChapter(nextChapter.id || nextChapter.chapterId)"
                class="hover:text-amber-500 transition-colors duration-300 flex items-center gap-2"
              >
                {{ nextChapter.title || '下一品' }} <span>→</span>
              </button>
              <div v-else></div>
            </div>
          </template>
        </SutraBody>
      </template>
    </div>

    <template v-if="bookMeta && chapterData">
      <!-- 禅听模式下显示播放条 -->
      <transition name="fade">
        <AudioPlayer
          v-if="mode === 'listening'"
          :currentTime="currentTime"
          :duration="duration"
          :isPlaying="isPlaying"
          :progress="progress"
          :voice="selectedVoice"
          @update:voice="onVoiceChange"
          v-model:autoPlay="autoPlayNext"
          v-model:isZenMode="isZenMode"
          @toggle="handleToggle"
          @seek="seekByPercent"
          class="audio-player-fixed"
        />
      </transition>
      
      <!-- Zen Mode (经典大字呼吸感禅定模式) -->
      <transition name="fade">
        <div 
          v-if="isZenMode" 
          class="fixed inset-0 z-[9999] bg-black flex items-center justify-center cursor-pointer select-none" 
          @click="isZenMode = false"
        >
          <div class="px-8 md:px-16 text-center zen-breathing-container" :class="{ 'is-paused': !isPlaying }">
            <div class="text-sm md:text-lg text-neutral-400 tracking-[0.4em] mb-8 font-serif uppercase">
              {{ isPlaying ? '正在持诵' : '已暂停' }} · {{ extractText(bookMeta?.title) }}
            </div>
            <div class="text-4xl sm:text-6xl md:text-7xl lg:text-8xl text-amber-100/75 tracking-[0.25em] font-serif leading-relaxed font-semibold zen-title-text">
              {{ extractText(chapterData?.title) }}
            </div>
          </div>
        </div>
      </transition>
    </template>
  </div>
</template>

<style scoped>
.reader-wrapper {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

.zen-title-text {
  text-shadow: 0 0 35px rgba(212, 175, 55, 0.45),
               0 0 70px rgba(212, 175, 55, 0.15);
}

@keyframes zen-breath {
  0% {
    opacity: 0.45;
    transform: scale(0.97);
  }
  100% {
    opacity: 1;
    transform: scale(1.03);
    text-shadow: 0 0 45px rgba(212, 175, 55, 0.6);
  }
}

.zen-breathing-container {
  animation: zen-breath 5s ease-in-out infinite alternate;
  will-change: opacity, transform;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.zen-breathing-container.is-paused {
  animation-duration: 12s;
  filter: opacity(0.7) brightness(0.8);
}

/* Top Navigation Buttons */
.nav-top-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 18px;
  border-radius: 9999px;
  background: rgba(18, 18, 24, 0.78);
  border: 1px solid rgba(212, 165, 116, 0.28);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: #ebdcc8;
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  line-height: 1;
  letter-spacing: 1px;
  pointer-events: auto;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-top-btn:hover {
  background: rgba(28, 28, 38, 0.9);
  border-color: rgba(212, 165, 116, 0.55);
  color: var(--gold);
  transform: translateY(-1px);
}

.nav-top-btn:active {
  transform: scale(0.96);
}

.nav-btn-icon {
  color: var(--gold);
  opacity: 0.85;
  flex-shrink: 0;
}

.nav-btn-text {
  display: inline-block;
  line-height: 1;
}

@media (max-width: 640px) {
  .nav-top-btn {
    padding: 7px 15px;
    font-size: 12px;
    gap: 5px;
  }
}

/* Drawer */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 200;
  backdrop-filter: blur(2px);
}

.drawer-content {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 320px;
  max-width: calc(100vw - 40px);
  background: rgba(14, 14, 20, 0.97);
  backdrop-filter: blur(28px) saturate(1.5);
  -webkit-backdrop-filter: blur(28px) saturate(1.5);
  border-left: 1px solid rgba(212, 165, 116, 0.2);
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.12);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-title-box h3 {
  margin: 0 0 4px;
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 3px;
  font-size: 17px;
  font-weight: 700;
}

.drawer-subtitle {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  transition: color 0.2s;
}

.close-btn:hover {
  color: var(--gold);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.chapter-item {
  padding: 13px 20px;
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-left: 3px solid transparent;
}

.chapter-item:hover {
  background: rgba(212, 165, 116, 0.06);
  color: var(--gold);
}

.chapter-item.active {
  color: var(--gold);
  background: rgba(212, 165, 116, 0.12);
  border-left-color: var(--gold);
}

.ch-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
  overflow: hidden;
}

.ch-num {
  font-family: monospace;
  font-size: 11px;
  color: var(--gold);
  opacity: 0.5;
  flex-shrink: 0;
}

.ch-title {
  font-size: 14px;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-audio {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 10px;
  font-family: 'Noto Serif SC', serif;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.3);
  color: var(--gold);
  flex-shrink: 0;
  letter-spacing: 0.5px;
}

.badge-text {
  font-size: 10px;
  color: var(--text-muted);
  opacity: 0.5;
  padding: 2px 6px;
  flex-shrink: 0;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: opacity 0.3s ease;
}

.slide-right-enter-active .drawer-content,
.slide-right-leave-active .drawer-content {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-right-enter-from .drawer-content,
.slide-right-leave-to .drawer-content {
  transform: translateX(100%);
}

.slide-right-enter-from,
.slide-right-leave-to {
  opacity: 0;
}

.audio-player-fixed {
  z-index: 100;
}
</style>
