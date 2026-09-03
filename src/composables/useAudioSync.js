/**
 * 音频播放与经文同步 Composable
 * 
 * 核心设计原则：
 * 1. 唯一真理来源 —— isPlaying 完全由原生 <audio> 事件驱动，禁止手动赋值
 * 2. Visibility API —— 后台回前台自动对齐状态，防止假死
 * 3. 零延迟同步接力 —— onEnded 同步切 src + play()，保住后台音频焦点
 * 4. 防御性 safePlay —— 捕获系统策略拒绝，自动回退 UI 状态
 */
import { ref, onUnmounted, computed, unref } from 'vue'

export function useAudioSync(paragraphs, options = {}) {
  const audio = new Audio()
  audio.preload = 'auto'
  const currentTime = ref(0)
  const duration = ref(0)
  const isPlaying = ref(false)
  const isLoaded = ref(false)
  const currentParagraphId = ref(-1)

  // 内部意图标记：业务逻辑认为"应该在播放"
  // 用于 Visibility API 回前台时判断是否需要恢复播放
  let _intendPlaying = false

  /** 进度百分比 0-100 */
  const progress = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
  )

  let rafId = null

  // ---- 二分查找当前段落 ----
  function findCurrentParagraph(time) {
    const ps = unref(paragraphs)
    if (!ps || ps.length === 0) return -1
    let lo = 0, hi = ps.length - 1, result = -1
    while (lo <= hi) {
      const mid = (lo + hi) >>> 1
      if (ps[mid].startTime <= time) {
        result = mid
        lo = mid + 1
      } else {
        hi = mid - 1
      }
    }
    if (result >= 0) {
      // 保持当前段落激活直到下一段开始，防止停顿空隙闪烁或失焦
      const nextStart = (result + 1 < ps.length) ? ps[result + 1].startTime : (ps[result].endTime + 1.5)
      if (time < nextStart) {
        return ps[result].id !== undefined ? ps[result].id : (result + 1)
      }
    }
    return -1
  }

  let _isVoiceSwitching = false

  // ---- rAF 循环 ----
  function tick() {
    if (!_isVoiceSwitching) {
      currentTime.value = audio.currentTime
      currentParagraphId.value = findCurrentParagraph(audio.currentTime)
    }
    rafId = requestAnimationFrame(tick)
  }

  function startLoop() {
    if (rafId) return
    rafId = requestAnimationFrame(tick)
  }

  function stopLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
  }

  // ============================================================
  //  1. 原生事件驱动 isPlaying —— 唯一真理来源
  // ============================================================
  audio.addEventListener('play', () => {
    isPlaying.value = true
    startLoop()
  })

  audio.addEventListener('playing', () => {
    isPlaying.value = true
    startLoop()
  })

  audio.addEventListener('pause', () => {
    isPlaying.value = false
    stopLoop()
  })

  audio.addEventListener('ended', () => {
    isPlaying.value = false
    stopLoop()
    // 检查是否开启单品循环
    if (options.getPlayMode && options.getPlayMode() === 'repeat-one') {
      audio.currentTime = 0
      safePlay()
      return
    }
    // 连播由外部通过 playNextTrack 在同步栈内完成
    if (options.onEnded) options.onEnded()
  })

  // 网络卡顿 / 系统挂起 —— 标记缓冲中但不影响意图
  audio.addEventListener('waiting', () => {
    // 保持 isPlaying = true（因为意图仍是播放），
    // 但可以在这里添加 loading 指示器
  })

  audio.addEventListener('suspend', () => {
    // iOS 后台可能触发 suspend，不主动改 isPlaying
    // 真正停止时系统会触发 pause 事件
  })

  audio.addEventListener('loadedmetadata', () => {
    duration.value = audio.duration
    isLoaded.value = true
  })

  // ============================================================
  //  2. Visibility API —— 后台唤醒状态对齐
  // ============================================================
  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // 回到前台：对齐检查
      if (_intendPlaying && audio.paused) {
        // 业务认为应该播放，但原生已暂停 → 重新激活
        safePlay()
      }
      // 同步一次时间，防止 rAF 在后台被冻结导致进度条跳跃
      currentTime.value = audio.currentTime
      if (!audio.paused && !rafId) {
        startLoop()
      }
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange)

  // ============================================================
  //  3. 防御性 safePlay —— 统一入口，捕获系统拒绝
  // ============================================================
  function safePlay() {
    _intendPlaying = true
    const promise = audio.play()
    if (promise && typeof promise.catch === 'function') {
      promise.catch((err) => {
        console.warn('[ChanYue] 播放被系统拒绝:', err.message)
        // 系统拒绝后，isPlaying 会被 pause 事件自动置 false
        // 但以防万一，手动兜底
        _intendPlaying = false
        isPlaying.value = false
        stopLoop()
      })
    }
  }

  // ---- Media Session API ----
  function setupMediaSession() {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.setActionHandler('play', () => { play() })
      navigator.mediaSession.setActionHandler('pause', () => { pause() })
      if (options.onPrev) {
        navigator.mediaSession.setActionHandler('previoustrack', options.onPrev)
      }
      if (options.onNext) {
        navigator.mediaSession.setActionHandler('nexttrack', options.onNext)
      }
    }
  }

  function updateMediaSession(meta) {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: meta.title || '未知章节',
        artist: meta.artist || '禅阅',
        album: meta.album || '禅阅',
        artwork: [
          { src: '/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512x512.png', sizes: '512x512', type: 'image/png' }
        ]
      })
    }
  }

  function loadAudio(url) {
    if (!audio.src.endsWith(url)) {
      audio.src = url
    }
    setupMediaSession()
  }

  /**
   * 无缝切换音色：精准保留当前播放秒数，顺畅接续念诵
   */
  function switchVoiceTrack(url) {
    if (!url) return
    const currentSrc = audio.src ? audio.src.split('?')[0] : ''
    if (currentSrc.endsWith(url)) return

    // 获取当前精准秒数（优先取 audio.currentTime，兜底 currentTime.value）
    const targetTime = Math.max(0, audio.currentTime || currentTime.value || 0)
    const wasPlaying = isPlaying.value || !audio.paused

    _isVoiceSwitching = true
    _intendPlaying = wasPlaying

    // 立即冻结当前秒数与高亮段落，避免换源瞬时归零闪烁
    currentTime.value = targetTime
    currentParagraphId.value = findCurrentParagraph(targetTime)

    let seekDone = false
    const doSeek = () => {
      if (seekDone) return
      if (targetTime > 0) {
        try {
          const maxSeek = (audio.duration && !isNaN(audio.duration)) ? Math.max(0, audio.duration - 0.2) : targetTime
          audio.currentTime = Math.min(targetTime, maxSeek)
          seekDone = true
        } catch (e) {
          console.warn('Seek error during voice switch:', e)
        }
      }
    }

    const onCanPlay = () => {
      audio.removeEventListener('canplay', onCanPlay)
      doSeek()
      if (wasPlaying && audio.paused) {
        safePlay()
      }
      setTimeout(() => {
        _isVoiceSwitching = false
      }, 250)
    }

    const onSeeked = () => {
      audio.removeEventListener('seeked', onSeeked)
      _isVoiceSwitching = false
    }

    audio.addEventListener('canplay', onCanPlay, { once: true })
    audio.addEventListener('seeked', onSeeked, { once: true })

    // 安全保护：1.5 秒后强行解除冻结，防止某些极端环境不触发事件
    setTimeout(() => {
      if (_isVoiceSwitching) {
        doSeek()
        _isVoiceSwitching = false
      }
    }, 1500)

    // 切源并加载
    audio.src = url
    audio.load()

    // 关键：在当前点击事件（用户手势活跃上下文）中同步调用 safePlay()
    // 确保移动端浏览器（iOS Safari / Android Chrome）维持媒体自动播放许可
    if (wasPlaying) {
      safePlay()
    }

    setupMediaSession()
  }

  /**
   * 零延迟同步接力 —— 连播核心
   * 
   * 在 onEnded 的同步执行栈内调用，
   * 立刻切 src + play()，让 OS 保持音频焦点不释放。
   * 路由跳转和数据加载由调用方异步处理。
   */
  function playNextTrack(url) {
    audio.src = url
    _intendPlaying = true
    safePlay()
  }

  function play() {
    safePlay()
  }

  function pause() {
    _intendPlaying = false
    audio.pause()
    // isPlaying 由 pause 事件自动置 false
  }

  function toggle() {
    audio.paused ? play() : pause()
  }

  function seek(time) {
    audio.currentTime = time
    currentTime.value = time
    currentParagraphId.value = findCurrentParagraph(time)
  }

  /** 按百分比 seek (0-100) */
  function seekByPercent(pct) {
    if (duration.value > 0) {
      seek((pct / 100) * duration.value)
    }
  }

  let _fadeTimer = null

  /**
   * 暮钟式音量平滑渐弱停止 (Sleep Timer Fade-out)
   * 在指定毫秒内将音量以对数/线性曲线从当前衰减至 0，随后暂停并复原音量基准
   */
  function fadeOutAndStop(durationMs = 8000) {
    if (!isPlaying.value && audio.paused) return
    if (_fadeTimer) clearInterval(_fadeTimer)
    const steps = 20
    const stepTime = Math.max(50, Math.floor(durationMs / steps))
    const initialVol = audio.volume || 1.0
    let currentStep = 0

    _fadeTimer = setInterval(() => {
      currentStep++
      const factor = Math.max(0, 1 - currentStep / steps)
      audio.volume = initialVol * factor
      if (currentStep >= steps || audio.volume <= 0.02) {
        clearInterval(_fadeTimer)
        _fadeTimer = null
        pause()
        audio.volume = 1.0
      }
    }, stepTime)
  }

  onUnmounted(() => {
    if (_fadeTimer) clearInterval(_fadeTimer)
    _intendPlaying = false
    stopLoop()
    audio.pause()
    audio.src = ''
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  return {
    currentTime,
    duration,
    isPlaying,
    isLoaded,
    currentParagraphId,
    progress,
    loadAudio,
    play,
    pause,
    toggle,
    seek,
    seekByPercent,
    updateMediaSession,
    playNextTrack,
    switchVoiceTrack,
    fadeOutAndStop,
  }
}
