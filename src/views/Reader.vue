<script setup>
import { ref, onMounted, onUnmounted, watch, shallowRef, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SutraHeader from '../components/SutraHeader.vue'
import ModeSelector from '../components/ModeSelector.vue'
import SutraBody from '../components/SutraBody.vue'
import AudioPlayer from '../components/AudioPlayer.vue'
import SearchModal from '../components/SearchModal.vue'
import { useAudioSync } from '../composables/useAudioSync.js'

const route = useRoute()
const router = useRouter()

const bookMeta = shallowRef(null)
const chapterData = shallowRef(null)
const mode = ref(route.query.mode || 'reading')
const showDrawer = ref(false)
const isLoading = ref(true)
const isSearchOpen = ref(false)

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

const selectedVoice = ref(localStorage.getItem('chanyue_voice') || 'female')

/**
 * 响应式动态音色时间戳适配：
 * 根据 selectedVoice 自动提取当前音色的专属时间戳（voices.female / voices.male），
 * 确保男女声切换时，段落 startTime 与行 lineStart 100% 毫秒级对齐。
 */
const activeParagraphs = computed(() => {
  const ps = chapterData.value?.paragraphs || []
  const voice = selectedVoice.value
  return ps.map(p => {
    const vTime = p.voices?.[voice]
    const pStart = vTime?.startTime ?? p.startTime
    const pEnd = vTime?.endTime ?? p.endTime
    return {
      ...p,
      startTime: pStart,
      endTime: pEnd,
      lines: (p.lines || []).map(l => {
        const lvTime = l.voices?.[voice]
        return {
          ...l,
          lineStart: lvTime?.lineStart ?? l.lineStart,
          lineEnd: lvTime?.lineEnd ?? l.lineEnd,
        }
      })
    }
  })
})

const paragraphsRef = activeParagraphs

function getVoiceAudioUrl(rawUrl, voice = selectedVoice.value) {
  if (!rawUrl) return rawUrl
  if (rawUrl.endsWith('.mp3')) {
    const base = rawUrl.slice(0, -4).replace(/_(female|male)$/, '')
    return `${base}_${voice}.mp3`
  }
  return rawUrl
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
  switchVoiceTrack,
} = useAudioSync(paragraphsRef, {
  onEnded: () => {
    // 播完单品自然停止
  },
  onNext: () => goToNextChapter(),
  onPrev: () => goToPrevChapter()
})

function onVoiceChange(newVoice) {
  selectedVoice.value = newVoice
  localStorage.setItem('chanyue_voice', newVoice)
  const rawUrl = chapterData.value?.audioUrl || bookMeta.value?.audioUrl
  if (rawUrl) {
    const targetUrl = getVoiceAudioUrl(rawUrl, newVoice)
    // 无缝接续：在当前播放秒数继续念诵
    switchVoiceTrack(targetUrl)
  }
}

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
  checkNavOverflow()
  setupNavObserver()
  if (typeof document !== 'undefined' && document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => checkNavOverflow())
  }
  window.addEventListener('resize', checkNavOverflow, { passive: true })
})

onUnmounted(() => {
  if (autoPlayTimer) clearTimeout(autoPlayTimer)
  window.removeEventListener('scroll', handleWindowScroll)
  window.removeEventListener('resize', checkNavOverflow)
  if (navResizeObserver) {
    navResizeObserver.disconnect()
    navResizeObserver = null
  }
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

const prevTrackRef = ref(null)
const nextTrackRef = ref(null)
const prevTitleRef = ref(null)
const nextTitleRef = ref(null)
const isPrevTitleOverflow = ref(false)
const isNextTitleOverflow = ref(false)

let navResizeObserver = null

function checkNavOverflow() {
  nextTick(() => {
    if (prevTrackRef.value && prevTitleRef.value) {
      const unit = prevTitleRef.value.querySelector('.nav-title-unit')
      if (unit) {
        const unitWidth = unit.scrollWidth || unit.getBoundingClientRect().width
        const trackWidth = prevTrackRef.value.clientWidth
        isPrevTitleOverflow.value = unitWidth > (trackWidth + 1)
      }
    } else {
      isPrevTitleOverflow.value = false
    }

    if (nextTrackRef.value && nextTitleRef.value) {
      const unit = nextTitleRef.value.querySelector('.nav-title-unit')
      if (unit) {
        const unitWidth = unit.scrollWidth || unit.getBoundingClientRect().width
        const trackWidth = nextTrackRef.value.clientWidth
        isNextTitleOverflow.value = unitWidth > (trackWidth + 1)
      }
    } else {
      isNextTitleOverflow.value = false
    }
  })
}

function setupNavObserver() {
  if (typeof ResizeObserver !== 'undefined') {
    if (!navResizeObserver) {
      navResizeObserver = new ResizeObserver(() => {
        checkNavOverflow()
      })
    }
    navResizeObserver.disconnect()
    if (prevTrackRef.value) navResizeObserver.observe(prevTrackRef.value)
    if (nextTrackRef.value) navResizeObserver.observe(nextTrackRef.value)
  }
}

watch([chapterId, prevChapter, nextChapter], () => {
  nextTick(() => {
    checkNavOverflow()
    setupNavObserver()
  })
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
      loadAudio(audioUrl)
    } else {
      if (!isAutoPlayingNext) pause()
      mode.value = 'reading'
    }
    isAutoPlayingNext = false
    
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

    // 若携带索经定位参数 hl，平滑滚动至对应经文并微光闪烁
    if (route.query.hl) {
      setTimeout(() => {
        const needle = decodeURIComponent(route.query.hl)
        const allLines = document.querySelectorAll('.sutra-line')
        for (const el of allLines) {
          if (el.textContent.includes(needle)) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' })
            el.classList.add('search-jump-flash')
            setTimeout(() => el.classList.remove('search-jump-flash'), 2500)
            break
          }
        }
      }, 500)
    }
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
  checkNavOverflow()
  window.addEventListener('resize', checkNavOverflow)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkNavOverflow)
})

/* 切换到阅读模式时暂停播放 */
watch(mode, (newMode) => {
  if (newMode === 'reading') {
    pause()
  }
})

const currentFirstPStart = computed(() => {
  const p0 = activeParagraphs.value?.[0]
  return p0?.startTime ?? 3.0
})

const isTitleActive = computed(() => isPlaying.value && currentTime.value < currentFirstPStart.value)

/* 诵读题目期间聚焦：当开始播放且处于诵读题目阶段时，第一时间聚焦滚动至顶部经题 */
watch(isTitleActive, (active) => {
  if (active && mode.value === 'listening') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
})

/* 点击播放时，自动切换到禅听模式并第一时间聚焦经题 */
function handleToggle() {
  if (mode.value === 'reading' && !isPlaying.value) {
    mode.value = 'listening'
  }
  if (!isPlaying.value && currentTime.value < currentFirstPStart.value) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  toggle()
}

</script>

<template>
  <div class="reader-wrapper min-h-screen w-full bg-[var(--bg-primary)] pb-6 md:pb-8">
    
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

      <div class="flex items-center gap-2 pointer-events-auto">
        <!-- 索经 -->
        <button class="nav-top-btn" @click.stop="isSearchOpen = true" title="跨经全文检索 (Cmd/Ctrl+K)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" class="nav-btn-icon">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span class="nav-btn-text">索经</span>
        </button>

        <!-- 经卷目录 (仅多章节经典显示，单卷经如心经直接沉浸阅读) -->
        <button v-if="bookMeta && bookMeta.chapters && bookMeta.chapters.length > 1" class="nav-top-btn" @click.stop="toggleDrawer">
          <span class="nav-btn-text">经卷目录</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="12" height="12" class="nav-btn-icon">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Chapter Drawer (器物级经卷目录抽屉) -->
    <transition name="slide-right">
      <div v-if="showDrawer && bookMeta?.chapters?.length > 1" class="drawer-overlay" @click.stop="toggleDrawer">
        <div class="drawer-content" @click.stop>
          <div class="drawer-header">
            <div class="drawer-title-box">
              <h3>经卷目录</h3>
              <p class="drawer-subtitle">{{ extractText(bookMeta?.title) }} · 共 {{ bookMeta?.chapters?.length }} 品</p>
            </div>
            <button class="close-btn" @click="toggleDrawer" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
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
            </div>
          </div>
          <div class="drawer-footer">
            <router-link to="/compare" class="drawer-compare-btn">
              <span>⚡ 声学母带对比实验室</span>
              <span>→</span>
            </router-link>
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
          :isTitleActive="isTitleActive"
        />

        <ModeSelector v-model:mode="mode" />

        <SutraBody
          :paragraphs="activeParagraphs"
          :currentParagraphId="currentParagraphId"
          :currentTime="currentTime"
          :mode="mode"
        >
          <template #footer>
            <!-- 经文诵毕 · 结经尾花印（古典经本落卷法印，一品圆满） -->
            <div class="chapter-end-seal">
              <span class="seal-glyph">◈</span>
            </div>

            <!-- 极简轻雅经品翻卷条（告别厚重大框，单侧居中，长品名自适应平滑跑马灯） -->
            <nav 
              v-if="prevChapter || nextChapter" 
              class="chapter-nav-bar" 
              :class="{ 
                'is-both': prevChapter && nextChapter, 
                'is-single': (!prevChapter && nextChapter) || (prevChapter && !nextChapter) 
              }"
              aria-label="经品导航"
            >
              <!-- 上一品 -->
              <button 
                v-if="prevChapter" 
                @click.stop="selectChapter(prevChapter.id || prevChapter.chapterId)"
                class="nav-btn prev"
                :title="`上一品：${prevChapter.title}`"
              >
                <span class="nav-arrow">←</span>
                <span class="nav-label">上一品</span>
                <span class="nav-sep">·</span>
                <div ref="prevTrackRef" class="nav-title-track" :class="{ 'is-scrolling': isPrevTitleOverflow }">
                  <div ref="prevTitleRef" class="nav-marquee-loop">
                    <div class="nav-marquee-part">
                      <span class="nav-title-unit">{{ prevChapter.title }}</span>
                      <span v-if="isPrevTitleOverflow" class="nav-marquee-sep">···</span>
                    </div>
                    <div v-if="isPrevTitleOverflow" class="nav-marquee-part" aria-hidden="true">
                      <span class="nav-title-unit">{{ prevChapter.title }}</span>
                      <span class="nav-marquee-sep">···</span>
                    </div>
                  </div>
                </div>
              </button>

              <!-- 下一品 -->
              <button 
                v-if="nextChapter" 
                @click.stop="selectChapter(nextChapter.id || nextChapter.chapterId)"
                class="nav-btn next"
                :title="`下一品：${nextChapter.title}`"
              >
                <div ref="nextTrackRef" class="nav-title-track" :class="{ 'is-scrolling': isNextTitleOverflow }">
                  <div ref="nextTitleRef" class="nav-marquee-loop">
                    <div class="nav-marquee-part">
                      <span class="nav-title-unit">{{ nextChapter.title }}</span>
                      <span v-if="isNextTitleOverflow" class="nav-marquee-sep">···</span>
                    </div>
                    <div v-if="isNextTitleOverflow" class="nav-marquee-part" aria-hidden="true">
                      <span class="nav-title-unit">{{ nextChapter.title }}</span>
                      <span class="nav-marquee-sep">···</span>
                    </div>
                  </div>
                </div>
                <span class="nav-sep">·</span>
                <span class="nav-label">下一品</span>
                <span class="nav-arrow">→</span>
              </button>
            </nav>
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
          @toggle="handleToggle"
          @seek="seekByPercent"
          class="audio-player-fixed"
        />
      </transition>
    </template>

    <!-- 全藏索经弹窗 -->
    <SearchModal v-model:visible="isSearchOpen" />
  </div>
</template>

<style scoped>
.reader-wrapper {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
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
}

.chapter-item:hover {
  background: rgba(212, 165, 116, 0.06);
  color: var(--gold);
}

.chapter-item.active {
  color: var(--gold);
  background: rgba(212, 165, 116, 0.12);
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

.drawer-footer {
  padding: 14px 20px;
  border-top: 1px solid rgba(212, 165, 116, 0.12);
  background: rgba(14, 14, 18, 0.5);
}

.drawer-compare-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.25);
  color: var(--gold);
  font-size: 13px;
  text-decoration: none;
  font-family: 'Noto Serif SC', serif;
  transition: all 0.25s ease;
}

.drawer-compare-btn:hover,
.drawer-compare-btn:active {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.5);
  transform: translateY(-1px);
}

/* 经文诵毕 · 结经尾花印（律动规范：经文末至印章 24px，印章至导航条 12px） */
.chapter-end-seal {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 24px;
  margin-bottom: 12px;
}

.seal-glyph {
  font-size: 14px;
  color: var(--gold);
  opacity: 0.4;
  letter-spacing: 4px;
  transition: all 0.3s ease;
}

.seal-glyph:hover {
  opacity: 0.85;
  text-shadow: 0 0 12px rgba(212, 165, 116, 0.4);
}

/* Chapter Pagination Footer (自适应宽度 + 极限小屏平滑跑马灯) */
.chapter-nav-bar {
  margin-top: 0;
  margin-bottom: 16px;
  padding: 0 12px;
  width: 100%;
  max-width: min(760px, 94%);
  margin-left: auto;
  margin-right: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  box-sizing: border-box;
}

.chapter-nav-bar.is-single {
  justify-content: center;
}

.chapter-nav-bar.is-both {
  justify-content: space-between;
}

.nav-btn {
  flex: 1 1 0;
  min-width: 0;
  max-width: calc(50% - 6px);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 9999px;
  background: rgba(22, 22, 28, 0.55);
  border: 1px solid rgba(212, 165, 116, 0.22);
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  overflow: hidden;
}

.chapter-nav-bar.is-single .nav-btn {
  flex: 0 1 auto;
  max-width: min(480px, 88%);
  padding: 8px 24px;
}

.nav-btn:hover {
  background: rgba(32, 32, 44, 0.75);
  border-color: rgba(212, 165, 116, 0.48);
  color: var(--gold);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
}

.nav-btn:active {
  transform: scale(0.97);
}

.nav-arrow {
  color: var(--gold);
  opacity: 0.8;
  font-size: 12px;
  flex-shrink: 0;
  transition: transform 0.25s ease;
}

.nav-btn.prev:hover .nav-arrow {
  transform: translateX(-3px);
}

.nav-btn.next:hover .nav-arrow {
  transform: translateX(3px);
}

.nav-label {
  flex-shrink: 0;
  color: var(--gold);
  opacity: 0.8;
  font-size: 12px;
  letter-spacing: 1px;
}

.nav-sep {
  flex-shrink: 0;
  color: rgba(212, 165, 116, 0.4);
  font-size: 11px;
}

/* 跑马灯滚动轨道：当文字溢出时两侧柔和羽化遮罩，无缝匀速滚动 */
.nav-title-track {
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
  position: relative;
  white-space: nowrap;
}

.nav-title-track.is-scrolling {
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%);
}

.nav-marquee-loop {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  line-height: 1.4;
  will-change: transform;
}

.nav-marquee-part {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  flex-shrink: 0;
}

.nav-title-track.is-scrolling .nav-marquee-loop {
  animation: continuousNavMarquee 9s linear infinite;
}

.nav-btn:hover .nav-marquee-loop,
.nav-btn:active .nav-marquee-loop {
  animation-play-state: paused;
}

@keyframes continuousNavMarquee {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

.nav-title-unit {
  display: inline-block;
  white-space: nowrap;
}

.nav-marquee-sep {
  display: inline-block;
  padding: 0 8px;
  color: var(--gold);
  opacity: 0.45;
  font-size: 11px;
  letter-spacing: 2px;
}

@media (max-width: 640px) {
  .chapter-end-seal {
    margin-top: 18px;
    margin-bottom: 10px;
  }
  .chapter-nav-bar {
    padding: 0 8px;
    gap: 8px;
    margin-bottom: 12px;
    max-width: 100%;
  }
  .nav-btn {
    padding: 6px 10px;
    font-size: 12px;
    gap: 4px;
    max-width: calc(50% - 4px);
  }
  .nav-label {
    font-size: 11px;
  }
  .nav-marquee-sep {
    padding: 0 6px;
  }
}

@media (max-width: 360px) {
  .chapter-nav-bar {
    padding: 0 4px;
    gap: 6px;
  }
  .nav-btn {
    padding: 5px 7px;
    font-size: 11.5px;
    gap: 3px;
    max-width: calc(50% - 3px);
  }
  .nav-sep {
    display: none;
  }
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

:deep(.search-jump-flash) {
  border-radius: 8px;
  animation: searchGlow 2.5s ease-out;
}

@keyframes searchGlow {
  0% { background: rgba(212, 165, 116, 0.35); box-shadow: 0 0 20px rgba(212, 165, 116, 0.4); }
  100% { background: transparent; box-shadow: none; }
}
</style>
