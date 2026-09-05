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
let userTouchTimer = null
let isUserTouching = false

function onUserTouchActivity() {
  isUserTouching = true
  if (userTouchTimer) clearTimeout(userTouchTimer)
  userTouchTimer = setTimeout(() => {
    isUserTouching = false
  }, 3500)
}

if (typeof window !== 'undefined') {
  window.addEventListener('touchstart', onUserTouchActivity, { passive: true })
  window.addEventListener('wheel', onUserTouchActivity, { passive: true })
}

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
      <template v-for="(char, ci) in line.chars" :key="ci">
        <ruby v-if="char.pinyin" class="sutra-char">
          {{ char.text }}<rt>{{ char.pinyin }}</rt>
        </ruby>
        <span v-else class="sutra-punct">{{ char.text }}</span>
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
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 2.4;
  margin-bottom: 4px;
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

/* 标点光学微排印：收紧过宽空白，更具雕版印刷致密感 */
.sutra-punct {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 24px;
  color: var(--text-muted);
  opacity: 0.8;
  margin: 0 -2px;
  display: inline-flex;
  align-items: flex-end;
  padding-bottom: 2px;
  transition: opacity 0.8s ease-in-out, color 0.8s ease-in-out;
}

.sutra-line.line-active .sutra-punct {
  color: var(--gold-muted);
  opacity: 0.85;
}



/* ===== 移动端 ===== */
@media (max-width: 640px) {
  .sutra-char    { font-size: 22px; }
  .sutra-char rt { font-size: 9px; }
  .sutra-punct   { font-size: 22px; }
  .sutra-paragraph { padding: 12px 4px; }
}
</style>
