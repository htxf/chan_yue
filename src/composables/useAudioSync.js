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
  const audio = typeof document !== 'undefined' ? document.createElement('audio') : new Audio()
  audio.style.display = 'none'
  audio.preload = 'auto'
  audio.setAttribute('playsinline', 'true')
  audio.setAttribute('webkit-playsinline', 'true')
  if (typeof document !== 'undefined' && document.body) {
    document.body.appendChild(audio)
  }

  // 纯网络层预载器：使用 fetch 静默预拉音频到 HTTP 磁盘/内存缓存，
  // 绝不创建第二个 <audio> 硬件节点，彻底杜绝移动端（iOS Safari/Android Chrome）AudioSession 锁冲突与解码器抢占
  function preloadTrack(url) {
    if (!url || typeof window === 'undefined') return
    try {
      fetch(url, { mode: 'no-cors' }).catch(() => {})
    } catch (e) {}
  }

  const currentTime = ref(0)
  const duration = ref(0)
  const isPlaying = ref(false)
  const isLoaded = ref(false)
  const currentParagraphId = ref(-1)

  // 内部意图标记：业务逻辑认为"应该在播放"
  // 用于切曲过渡与 Visibility API 回前台判断
  let _intendPlaying = false
  let _retryTimer = null
  let _retryCount = 0

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
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = 'playing'
    }
    updatePositionState()
  })

  audio.addEventListener('playing', () => {
    _retryCount = 0
    isPlaying.value = true
    startLoop()
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = 'playing'
    }
    updatePositionState()
  })

  audio.addEventListener('pause', () => {
    // 关键：如果内部意图仍在播放（如切曲接力中途触发的短暂原生 pause），不提前置 false，避免锁屏状态抖动
    if (!_intendPlaying) {
      isPlaying.value = false
      stopLoop()
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'paused'
      }
      updatePositionState()
    }
  })

  // 原生 timeupdate 事件驱动：在手机锁屏/熄屏导致 rAF 循环被挂起时，依然保证时间与高亮段落精准对齐！
  audio.addEventListener('timeupdate', () => {
    if (!_isVoiceSwitching) {
      currentTime.value = audio.currentTime
      currentParagraphId.value = findCurrentParagraph(audio.currentTime)
    }
  })

  audio.addEventListener('ended', () => {
    stopLoop()
    // 检查是否开启单品循环
    const mode = options.getPlayMode ? options.getPlayMode() : ''
    if (mode === 'repeat-one') {
      audio.currentTime = 0
      safePlay()
      return
    }

    // 连播由外部通过 onEnded -> playNextTrack 在同一同步栈内完成
    // 关键：不要在此处将 mediaSession.playbackState 盲目设为 paused，避免手机系统判定会话结束而销毁后台常驻锁！
    if (options.onEnded) {
      options.onEnded()
    }

    // 若外部未发起接力播放（未触发 playNextTrack），此时 audio 仍为暂停且意图结束，正式设为 paused
    if (audio.paused && !_intendPlaying) {
      isPlaying.value = false
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'paused'
      }
    }
  })

  // 健壮容错与网络自愈重试
  audio.addEventListener('error', (e) => {
    const err = audio.error
    console.warn('[ChanYue Audio Error]:', err ? `code=${err.code}, message=${err.message}` : e)
    if (_intendPlaying && _retryCount < 3) {
      _retryCount++
      console.info(`[ChanYue Audio] 网络自愈重试第 ${_retryCount} 次...`)
      if (_retryTimer) clearTimeout(_retryTimer)
      _retryTimer = setTimeout(() => {
        if (_intendPlaying && audio.paused) {
          audio.load()
          safePlay()
        }
      }, 600 * _retryCount)
    } else {
      _retryCount = 0
      isPlaying.value = false
      _intendPlaying = false
      stopLoop()
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'paused'
      }
    }
  })

  // 网络卡顿 / 系统挂起 —— 标记缓冲中但不影响意图
  audio.addEventListener('waiting', () => {
    // 保持 isPlaying = true（因为意图仍是播放）
  })

  audio.addEventListener('suspend', () => {
    // iOS 后台可能触发 suspend，不主动改 isPlaying
  })

  audio.addEventListener('loadedmetadata', () => {
    duration.value = audio.duration
    isLoaded.value = true
    updatePositionState()
  })

  // ============================================================
  //  2. Visibility API —— 后台唤醒状态对齐
  // ============================================================
  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // 回到前台：对齐检查，若此前应在播放但处于暂停或异常中断，自动自愈唤醒
      if (_intendPlaying && audio.paused) {
        play()
      }
      // 同步一次时间，防止 rAF 在后台被冻结导致进度条跳跃
      currentTime.value = audio.currentTime
      if (!audio.paused && !rafId) {
        startLoop()
      }
      updatePositionState()
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange)

  // ============================================================
  //  3. 防御性 safePlay —— 统一入口，捕获系统拒绝并自愈
  // ============================================================
  function safePlay() {
    _intendPlaying = true
    const promise = audio.play()
    if (promise && typeof promise.catch === 'function') {
      promise.catch((err) => {
        if (err.name === 'AbortError') {
          // 切曲或重载打断上一曲请求属于正常竞态，保留播放意图
          return
        }
        console.warn('[ChanYue] 播放暂未就绪或被拦截:', err.message || err.name)
        // 若业务意图仍在播放中（如后台切品），绝不立即放弃，执行自愈重载重试
        if (_intendPlaying && _retryCount < 3) {
          _retryCount++
          console.info(`[ChanYue] 正在执行第 ${_retryCount} 次起播自愈...`)
          if (_retryTimer) clearTimeout(_retryTimer)
          _retryTimer = setTimeout(() => {
            if (_intendPlaying && audio.paused) {
              try {
                audio.load()
              } catch (e) {}
              const p = audio.play()
              if (p && p.catch) p.catch(() => {})
            }
          }, 600 * _retryCount)
        } else {
          _retryCount = 0
          _intendPlaying = false
          isPlaying.value = false
          stopLoop()
          if ('mediaSession' in navigator) {
            navigator.mediaSession.playbackState = 'paused'
          }
        }
      })
    }
  }

  // ---- Media Session API ----
  function updatePositionState() {
    if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession) {
      if (duration.value > 0 && !isNaN(duration.value) && !isNaN(audio.currentTime)) {
        try {
          navigator.mediaSession.setPositionState({
            duration: Math.max(0.1, duration.value),
            playbackRate: audio.playbackRate || 1,
            position: Math.min(Math.max(0, audio.currentTime), duration.value)
          })
        } catch (e) {}
      }
    }
  }

  function setupMediaSession() {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.setActionHandler('play', () => { play() })
      navigator.mediaSession.setActionHandler('pause', () => { pause() })
      if (options.onPrev) {
        navigator.mediaSession.setActionHandler('previoustrack', () => { options.onPrev() })
      }
      if (options.onNext) {
        navigator.mediaSession.setActionHandler('nexttrack', () => { options.onNext() })
      }
      try {
        navigator.mediaSession.setActionHandler('seekto', (details) => {
          if (details.seekTime !== undefined) {
            seek(details.seekTime)
          }
        })
      } catch (e) {}
    }
  }

  function updateMediaSession(meta) {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: meta.title || '未知章节',
        artist: meta.artist || '禅阅',
        album: meta.album || '禅阅',
        artwork: [
          { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' }
        ]
      })
      updatePositionState()
    }
  }

  function resetAudio() {
    _intendPlaying = false
    try {
      audio.pause()
      audio.currentTime = 0
    } catch (e) {}
    currentTime.value = 0
    currentParagraphId.value = -1
    duration.value = 0
    isPlaying.value = false
    stopLoop()
  }

  function loadAudio(url) {
    if (!url) return
    const currentSrc = audio.src ? audio.src.split('?')[0] : ''
    // 若当前 audio 已指向该音频且处于健康就绪状态，无需重复 reset
    if (currentSrc && currentSrc.endsWith(url) && !audio.error && audio.readyState > 0) {
      setupMediaSession()
      return
    }
    resetAudio()
    audio.src = url
    try {
      audio.load()
    } catch (e) {}
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
   * 立刻切 src + load() + play()，让 OS 保持音频焦点不释放。
   * 路由跳转和数据加载由调用方异步处理。
   */
  function playNextTrack(url) {
    if (!url) return
    const currentSrc = audio.src ? audio.src.split('?')[0] : ''
    if (!currentSrc.endsWith(url) || audio.error) {
      audio.src = url
      try {
        audio.load()
      } catch (e) {}
    }
    try {
      audio.currentTime = 0
    } catch (e) {}
    currentTime.value = 0
    currentParagraphId.value = -1
    _retryCount = 0
    _intendPlaying = true
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = 'playing'
    }
    safePlay()
    setupMediaSession()
  }

  function play() {
    _retryCount = 0
    _intendPlaying = true
    // 自愈防御：若当前处于错误状态、无源或未就绪，重载音频管道，彻底消除“必须刷新页面才能重新播放”的问题
    if (audio.error || !audio.src || audio.networkState === HTMLMediaElement.NETWORK_NO_SOURCE || audio.readyState === 0) {
      console.info('[ChanYue] audio 处于异常或未就绪状态，强制重载管道...')
      try {
        if (!audio.src && options.getCurrentAudioUrl) {
          audio.src = options.getCurrentAudioUrl()
        }
        audio.load()
      } catch (e) {}
    }
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
    if (_retryTimer) clearTimeout(_retryTimer)
    _intendPlaying = false
    stopLoop()
    audio.pause()
    audio.src = ''
    if (audio.parentNode) {
      audio.parentNode.removeChild(audio)
    }
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
    preloadTrack,
    switchVoiceTrack,
    fadeOutAndStop,
    resetAudio,
  }
}
