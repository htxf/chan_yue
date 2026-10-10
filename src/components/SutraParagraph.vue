<!--
  SutraParagraph - 单段经文渲染
  逐行呼吸式高亮：
  - 监听 currentTime，比对 line.lineStart/lineEnd 确定激活行
  - 整行容器 opacity 过渡，绝不逐字闪烁
  - 激活行自动 scrollIntoView 居中
-->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  paragraph: Object,
  active: Boolean,
  index: Number,
  currentTime: { type: Number, default: 0 },
  /** 'reading' | 'listening' */
  mode: { type: String, default: 'reading' },
})

const lineRefs = ref([])
const paragraphEl = ref(null)

/**
 * 当前激活的行索引（-1 表示无）
 * 仅禅听模式下生效
 */
const activeLineIndex = computed(() => {
  if (props.mode !== 'listening') return -1
  const t = props.currentTime
  const lines = props.paragraph?.lines
  if (!lines || lines.length === 0) return -1
  
  let lo = 0, hi = lines.length - 1, result = -1
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1
    if (lines[mid].lineStart <= t) {
      result = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  if (result >= 0) {
    const nextStart = (result + 1 < lines.length) ? lines[result + 1].lineStart : (lines[result].lineEnd + 2.0)
    if (t < nextStart) {
      return result
    }
  }
  return -1
})

let lastScrolledLine = -1

// 模块级单例监听器：全生命周期仅向 window 挂载一次，杜绝多实例重复绑定导致的内存泄露
let isUserTouching = false
let userTouchTimer = null
let isTouchListenerInitialized = false

function initSingletonTouchListener() {
  if (isTouchListenerInitialized || typeof window === 'undefined') return
  const onUserTouchActivity = (e) => {
    // 排除点击控制栏、播放器或导航按钮触发的误判
    if (e?.target?.closest?.('.audio-player-fixed, .audio-player-card, button, .nav-top-btn, .mode-selector')) {
      return
    }
    isUserTouching = true
    if (userTouchTimer) clearTimeout(userTouchTimer)
    userTouchTimer = setTimeout(() => {
      isUserTouching = false
    }, 2000)
  }
  window.addEventListener('touchstart', onUserTouchActivity, { passive: true })
  window.addEventListener('wheel', onUserTouchActivity, { passive: true })
  isTouchListenerInitialized = true
}

initSingletonTouchListener()

/* 仅在激活行真正前进变化时丝滑居中滚动，用户手动翻阅时智能防打架 */
watch([() => props.active, activeLineIndex], async ([isActive, lineIdx]) => {
  if (props.mode !== 'listening' || !isActive) {
    lastScrolledLine = -1
    return
  }
  
  if (lineIdx >= 0 && lineIdx !== lastScrolledLine) {
    lastScrolledLine = lineIdx
    // 用户正在触摸翻阅时，暂停自动强行回拉，避免打架
    if (!isUserTouching) {
      await nextTick()
      const el = lineRefs.value[lineIdx]
      if (el) {
        const rect = el.getBoundingClientRect()
        const vh = window.innerHeight || document.documentElement.clientHeight
        const elementCenter = rect.top + rect.height / 2
        const viewportCenter = vh * 0.48
        // 偏离舒适阅读中心超 45px 时才平滑移动，杜绝紧邻短行每隔一两秒高频微抖
        if (Math.abs(elementCenter - viewportCenter) > 45) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }
    }
  }
})

// 避头尾标点符号集合 (W3C CLReq 中文排版国际标准规范)
const LEADING_PUNCT = new Set(['「', '『', '（', '(', '[', '{', '“', '‘', '《'])
const TRAILING_PUNCT = new Set(['，', '。', '、', '：', '；', '？', '！', '”', '’', '』', '」', '）', ')', ']', '}', '》', '—', '…'])

/**
 * 将行内字符与标点组合为不可拆分的字标物理单元 (GlyphUnit)
 * 彻底杜绝手机小屏幕上标点被挤到下一行开头或独立成行的不友好现象
 */
function getLineUnits(chars) {
  if (!chars || chars.length === 0) return []
  const units = []
  let pendingLeading = ''

  for (let i = 0; i < chars.length; i++) {
    const c = chars[i]
    const t = c.text
    if (!t || t === '\n' || t === '\r' || t.trim() === '') continue

    // 前置避尾标点：暂存并与下一个汉字绑定
    if (LEADING_PUNCT.has(t)) {
      pendingLeading += t
      continue
    }

    // 后置避头标点：紧密粘合在上一个汉字后面
    if (TRAILING_PUNCT.has(t)) {
      if (units.length > 0) {
        units[units.length - 1].trailing += t
      } else {
        pendingLeading += t
      }
      continue
    }

    // 汉字主体
    units.push({
      char: c,
      leading: pendingLeading,
      trailing: ''
    })
    pendingLeading = ''
  }

  // 极端纯标点兜底
  if (units.length === 0 && pendingLeading) {
    units.push({
      char: { text: pendingLeading },
      leading: '',
      trailing: ''
    })
  }

  return units
}
</script>

<template>
  <div
    ref="paragraphEl"
    class="sutra-paragraph"
    :class="[`mode-${mode}`, { active }]"
  >
    <div
      v-for="(line, li) in paragraph.lines"
      :key="li"
      :ref="(el) => { lineRefs[li] = el }"
      class="sutra-line"
      :class="{
        'line-active': mode === 'listening' && activeLineIndex === li,
        'line-dim':    mode === 'listening' && activeLineIndex !== li,
      }"
    >
      <template v-for="(unit, ui) in getLineUnits(line.chars)" :key="ui">
        <span class="sutra-glyph-unit">
          <span v-if="unit.leading" class="sutra-punct leading">{{ unit.leading }}</span>
          <ruby v-if="unit.char.pinyin" class="sutra-char">
            {{ unit.char.text }}<rt>{{ unit.char.pinyin }}</rt>
          </ruby>
          <span v-else class="sutra-char">{{ unit.char.text }}</span>
          <span v-if="unit.trailing" class="sutra-punct trailing">{{ unit.trailing }}</span>
        </span>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* ===== 段落容器 ===== */
.sutra-paragraph {
  padding: 16px 8px;
  border-radius: 8px;
  transition: opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 阅读模式：全亮 */
.sutra-paragraph.mode-reading {
  opacity: 1;
  transform: scale(1);
}

/* 禅听模式：非激活段落整体淡出 */
.sutra-paragraph.mode-listening:not(.active) {
  opacity: 0.25;
  transform: scale(0.97);
}

/* 禅听模式：激活段落容器全亮 */
.sutra-paragraph.mode-listening.active {
  opacity: 1;
  transform: scale(1);
}

/* ===== 行级呼吸高亮 ===== */
.sutra-line {
  display: flex;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 2px 4px;
  line-height: 2.3;
  margin-bottom: 6px;
  /* 呼吸过渡：opacity + text-shadow 同步渐变，绝不闪烁 */
  transition: opacity 0.8s ease-in-out,
              text-shadow 0.8s ease-in-out;
}

.sutra-line:last-child {
  margin-bottom: 0;
}

/* 未激活行：半透明沉睡 */
.sutra-line.line-dim {
  opacity: 0.35;
}

/* 当前激活行：缓缓亮起 + 双层烛火微光暖晕 */
.sutra-line.line-active {
  opacity: 1;
  text-shadow: 0 0 10px rgba(212, 165, 116, 0.65),
               0 0 28px rgba(212, 165, 116, 0.22);
}

/* ===== 字符样式 ===== */
.sutra-char {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-weight: 700;
  font-size: 28px;
  color: var(--text-primary);
  letter-spacing: 2px;
}

/* 禅听模式激活行：字色提亮为温暖金砂 */
.sutra-line.line-active .sutra-char {
  color: var(--gold);
  transition: color 0.8s ease-in-out;
}

/* 禅听模式非激活行：字色回归深邃中性 */
.sutra-line.line-dim .sutra-char {
  color: var(--text-muted);
  transition: color 0.8s ease-in-out;
}

.sutra-char rt {
  font-family: var(--font-pinyin);
  font-weight: 400;
  font-size: 13px;
  color: var(--text-primary);
  padding-bottom: 4px;
  letter-spacing: 0;
  transition: color 0.8s ease-in-out;
}

.sutra-line.line-active rt {
  color: var(--gold-muted);
}

.sutra-line.line-dim rt {
  color: var(--text-muted);
  opacity: 0.8;
}

/* ===== 字标原子粘合单元 (Glyph Unit) ===== */
.sutra-glyph-unit {
  display: inline-flex;
  align-items: baseline;
  white-space: nowrap; /* 核心铁律：汉字与前后附丽标点同生共进，绝对杜绝被折行拆散 */
  flex-shrink: 0;
}

/* 标点光学微排印：收紧过宽空白，避免小屏无意义断行 */
.sutra-punct {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 24px;
  color: var(--text-muted);
  opacity: 0.8;
  display: inline-block;
  line-height: 1;
  transition: opacity 0.8s ease-in-out, color 0.8s ease-in-out;
}

.sutra-punct.leading {
  margin-right: -2px;
}

.sutra-punct.trailing {
  margin-left: 1px;
  margin-right: -4px; /* 标点右侧留白光学压缩，提升每行排字密度 */
}

.sutra-line.line-active .sutra-punct {
  color: var(--gold-muted);
  opacity: 0.85;
}

/* ===== 移动端 ===== */
@media (max-width: 640px) {
  .sutra-line    { gap: 2px 3px; line-height: 2.2; }
  .sutra-char    { font-size: 21px; letter-spacing: 1px; }
  .sutra-char rt { font-size: 9px; padding-bottom: 2px; }
  .sutra-punct   { font-size: 20px; }
  .sutra-paragraph { padding: 10px 2px; }
}

/* ===== 电脑宽屏（>= 1024px）：字号与间距等比舒展，单行饱满，消除断尾 ===== */
@media (min-width: 1024px) {
  .sutra-line    { gap: 3px 6px; line-height: 2.35; margin-bottom: 8px; }
  .sutra-char    { font-size: 30px; letter-spacing: 2.5px; }
  .sutra-char rt { font-size: 13.5px; padding-bottom: 4px; }
  .sutra-punct   { font-size: 26px; }
  .sutra-paragraph { padding: 20px 12px; }
}

@media (min-width: 1440px) {
  .sutra-line    { gap: 4px 7px; line-height: 2.4; margin-bottom: 10px; }
  .sutra-char    { font-size: 32px; letter-spacing: 3px; }
  .sutra-char rt { font-size: 14px; padding-bottom: 5px; }
  .sutra-punct   { font-size: 28px; }
  .sutra-paragraph { padding: 24px 16px; }
}
</style>
