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
  return props.paragraph.lines.findIndex(
    (line) => t >= line.lineStart && t < line.lineEnd
  )
})

/* 当段落激活或激活行变化时，丝滑滚动到屏幕中央 */
watch([() => props.active, activeLineIndex], async ([isActive, lineIdx]) => {
  if (props.mode !== 'listening' || !isActive) return
  
  await nextTick()
  const el = (lineIdx >= 0 && lineRefs.value[lineIdx]) ? lineRefs.value[lineIdx] : paragraphEl.value
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
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

/* 当前激活行：缓缓亮起 + 柔光 */
.sutra-line.line-active {
  opacity: 1;
  text-shadow: 0 0 16px rgba(212, 165, 116, 0.45),
               0 0 32px rgba(212, 165, 116, 0.15);
}

/* ===== 字符样式 ===== */
.sutra-char {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-weight: 700;
  font-size: 28px;
  color: var(--text-primary);
  letter-spacing: 2px;
}

/* 禅听模式激活行：字色提亮为金色 */
.sutra-line.line-active .sutra-char {
  color: var(--gold);
  transition: color 0.8s ease-in-out;
}

/* 禅听模式非激活行：字色回归中性 */
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
  opacity: 0.6;
}

.sutra-punct {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 28px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: flex-end;
  padding-bottom: 2px;
}



/* ===== 移动端 ===== */
@media (max-width: 640px) {
  .sutra-char    { font-size: 22px; }
  .sutra-char rt { font-size: 9px; }
  .sutra-punct   { font-size: 22px; }
  .sutra-paragraph { padding: 12px 4px; }
}
</style>
