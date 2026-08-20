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

onUnmounted(() => {
  if (autoPlayTimer) clearTimeout(autoPlayTimer)
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
  <div class="reader-wrapper min-h-screen w-full bg-[#1a1a1a]">
    
    <!-- Top Controls -->
    <div 
      class="fixed top-5 left-5 right-5 z-[100] flex justify-between pointer-events-none transition-opacity duration-500 ease-out"
      :class="isLoading ? 'opacity-0' : 'opacity-100'"
    >
      <button class="pointer-events-auto flex items-center gap-2 md:gap-3 font-serif text-sm text-gray-500 hover:text-amber-200/80 transition-colors duration-300" @click.stop="goBack">
        <span class="text-xl md:text-base">〈</span> <span class="hidden md:inline">返回书阁</span>
      </button>
      <button v-if="bookMeta && bookMeta.chapters && bookMeta.chapters.length > 1" class="pointer-events-auto flex items-center gap-2 md:gap-3 font-serif text-sm text-gray-500 hover:text-amber-200/80 transition-colors duration-300" @click.stop="toggleDrawer">
        <span class="hidden md:inline">目录</span> <span class="text-xl md:text-base">☰</span>
      </button>
    </div>

    <!-- Chapter Drawer -->
    <transition name="slide-right">
      <div v-if="showDrawer" class="drawer-overlay" @click.stop="toggleDrawer">
        <div class="drawer-content" @click.stop>
          <div class="drawer-header">
            <h3>目录</h3>
            <button class="close-btn" @click="toggleDrawer">×</button>
          </div>
          <div class="drawer-body">
            <div 
              v-for="chapter in bookMeta.chapters" 
              :key="chapter.id || chapter.chapterId"
              class="chapter-item"
              :class="{ active: (chapter.id || chapter.chapterId) === chapterId }"
              @click="selectChapter(chapter.id || chapter.chapterId)"
            >
              {{ chapter.title }}
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
          :author="bookMeta.author"
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
  width: 280px;
  background: #111;
  border-left: 1px solid rgba(212, 175, 55, 0.2);
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  padding: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-header h3 {
  margin: 0;
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 4px;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 24px;
  cursor: pointer;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.chapter-item {
  padding: 16px 24px;
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  cursor: pointer;
  transition: background 0.2s;
  letter-spacing: 2px;
}

.chapter-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.chapter-item.active {
  color: var(--gold);
  background: rgba(212, 175, 55, 0.1);
  border-left: 3px solid var(--gold);
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
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
}
</style>
