<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: [Array, String],
  subtitle: [Array, String],
  author: [Array, String],
  isFirstChapter: {
    type: Boolean,
    default: true,
  },
  isMultiChapter: {
    type: Boolean,
    default: false,
  },
  isTitleActive: {
    type: Boolean,
    default: false,
  },
})

const normalize = (val) => {
  if (!val) return []
  if (Array.isArray(val)) return val
  return String(val).split('').map(char => ({ text: char }))
}

const nTitle = computed(() => normalize(props.title))
const nSubtitle = computed(() => normalize(props.subtitle))
const nAuthor = computed(() => normalize(props.author))

const rawTitleText = computed(() => {
  if (typeof props.title === 'string') return props.title
  if (Array.isArray(props.title)) {
    return props.title.map(c => typeof c === 'object' ? c.text : c).join('')
  }
  return '金刚经'
})
</script>

<template>
  <header class="sutra-header" :class="{ 'is-subsequent': isMultiChapter && !isFirstChapter }">
    <!-- 情况一：多章节经典的第一品（如《金刚经》卷首：全经总题 -> 译署署名 -> 第一品品题） -->
    <template v-if="isMultiChapter && isFirstChapter">
      <!-- 1. 全经总题 -->
      <h2 class="book-grand-title">
        <ruby v-for="(char, i) in nTitle" :key="`t-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h2>

      <!-- 2. 译署署名（紧随全经总题之后，大藏经正统排版规范） -->
      <p v-if="nAuthor.length" class="sutra-author">
        <ruby v-for="(char, i) in nAuthor" :key="`a-${i}`">
          <template v-if="char.text !== ' '">{{ char.text }}</template>
          <span v-else>&nbsp;&nbsp;</span>
          <rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </p>

      <!-- 3. 第一品品题（作为当前持诵主标题，统一享受烛火金晕） -->
      <h1 
        v-if="nSubtitle.length" 
        class="sutra-title chapter-hero-title first-chapter-hero"
        :class="{ 'is-title-glowing': isTitleActive }"
      >
        <ruby v-for="(char, i) in nSubtitle" :key="`s-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h1>
    </template>

    <!-- 情况二：多章节经典的后续品目（第二品至第三十二品） -->
    <template v-else-if="isMultiChapter && !isFirstChapter">
      <div class="book-badge">
        <span class="badge-name">{{ rawTitleText }}</span>
      </div>
      <h1 class="sutra-title chapter-hero-title" :class="{ 'is-title-glowing': isTitleActive }">
        <ruby v-for="(char, i) in (nSubtitle.length ? nSubtitle : nTitle)" :key="`ch-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h1>
    </template>

    <!-- 情况三：单卷经典（如《心经》：全经总题 -> 译署署名，不重复堆叠） -->
    <template v-else>
      <h1 class="sutra-title chapter-hero-title" :class="{ 'is-title-glowing': isTitleActive }">
        <ruby v-for="(char, i) in (nSubtitle.length ? nSubtitle : nTitle)" :key="`x-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h1>
      <p v-if="nAuthor.length" class="sutra-author single-sutra-author">
        <ruby v-for="(char, i) in nAuthor" :key="`xa-${i}`">
          <template v-if="char.text !== ' '">{{ char.text }}</template>
          <span v-else>&nbsp;&nbsp;</span>
          <rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </p>
    </template>

    <div class="divider">
      <span class="divider-dot"></span>
      <span class="divider-line"></span>
      <span class="divider-dot"></span>
    </div>
  </header>
</template>

<style scoped>
.sutra-header {
  padding: 88px 20px 36px;
  text-align: center;
  animation: headerFadeIn 1.2s ease both;
}

.sutra-header.is-subsequent {
  padding: 80px 20px 32px;
}

/* 卷首全经总题 */
.book-grand-title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-weight: 700;
  font-size: 26px;
  letter-spacing: 8px;
  color: var(--text-primary);
  margin: 0 0 12px;
  line-height: 1.8;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 2px;
}

.book-grand-title ruby { margin-right: 4px; }
.book-grand-title rt {
  font-family: var(--font-pinyin);
  font-size: 11.5px;
  font-weight: 400;
  color: var(--text-primary);
  opacity: 0.8;
  padding-bottom: 2px;
  letter-spacing: 0;
}

/* 经名上方微缩胶囊徽章（第二品及以后） */
.book-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  padding: 3px 14px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.16);
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  font-size: 12.5px;
  letter-spacing: 2.5px;
  opacity: 0.85;
}

/* 本品品题 / 核心主标题 */
.chapter-hero-title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-weight: 900;
  font-size: 30px;
  letter-spacing: 8px;
  color: var(--gold);
  margin: 0 0 16px;
  line-height: 1.8;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 2px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.first-chapter-hero {
  margin-top: 20px;
}

.chapter-hero-title ruby { margin-right: 6px; }

.chapter-hero-title rt {
  font-family: var(--font-pinyin);
  font-size: 13px;
  font-weight: 400;
  color: var(--gold);
  opacity: 0.85;
  padding-bottom: 2px;
  letter-spacing: 0;
}

/* 译署署名 */
.sutra-author {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 14.5px;
  color: var(--text-muted);
  letter-spacing: 3.5px;
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 2px;
  opacity: 0.95;
}

.single-sutra-author {
  margin-top: 14px;
}

.sutra-author ruby { margin-right: 2px; }

.sutra-author rt {
  font-family: var(--font-pinyin);
  font-size: 10.5px;
  color: var(--text-muted);
  opacity: 0.95;
  padding-bottom: 2px;
  letter-spacing: 0;
}

/* 烛火金晕高亮（朗读品题时） */
.is-title-glowing {
  color: var(--gold) !important;
  text-shadow: 0 0 16px rgba(212, 165, 116, 0.85), 0 0 36px rgba(212, 165, 116, 0.45) !important;
  transform: scale(1.02);
}

/* 分隔微符 */
.divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 28px;
}

.divider-line {
  width: 80px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-dim), transparent);
}

.divider-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--gold-dim);
}

@keyframes headerFadeIn {
  from { opacity: 0; transform: translateY(-16px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 640px) {
  .sutra-header { padding: 76px 16px 28px; }
  .sutra-header.is-subsequent { padding: 70px 16px 24px; }
  .book-grand-title { font-size: 22px; letter-spacing: 5px; }
  .chapter-hero-title { font-size: 24px; letter-spacing: 5px; }
  .first-chapter-hero { margin-top: 16px; }
}
</style>
