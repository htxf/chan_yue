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
  <header class="sutra-header" :class="{ 'is-subsequent': !isFirstChapter }">
    <!-- 第一品 / 卷首：展示全套经名大标题、译者、第一品名 -->
    <template v-if="isFirstChapter">
      <div class="ornament">◈</div>
      <h1 class="sutra-title">
        <ruby v-for="(char, i) in nTitle" :key="`t-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h1>
      <h2 v-if="nSubtitle.length" class="sutra-subtitle">
        <ruby v-for="(char, i) in nSubtitle" :key="`s-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h2>
      <p v-if="nAuthor.length" class="sutra-author">
        <ruby v-for="(char, i) in nAuthor" :key="`a-${i}`">
          <template v-if="char.text !== ' '">{{ char.text }}</template>
          <span v-else>&nbsp;&nbsp;</span>
          <rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </p>
    </template>

    <!-- 第二品及以后：品名提升为主标题，经名缩减为上方雅致徽章 -->
    <template v-else>
      <div class="book-badge">
        <span class="badge-dot">◈</span>
        <span class="badge-name">{{ rawTitleText }}</span>
        <span class="badge-dot">◈</span>
      </div>
      <h1 class="sutra-title chapter-hero-title">
        <ruby v-for="(char, i) in (nSubtitle.length ? nSubtitle : nTitle)" :key="`ch-${i}`">
          {{ char.text }}<rt v-if="char.pinyin">{{ char.pinyin }}</rt>
        </ruby>
      </h1>
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
  padding: 60px 20px 40px;
  text-align: center;
  animation: headerFadeIn 1.2s ease both;
}

.sutra-header.is-subsequent {
  padding: 44px 20px 28px;
}

.book-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 4px 14px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.18);
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 3px;
  opacity: 0.85;
}

.badge-dot {
  font-size: 10px;
  opacity: 0.6;
}

.chapter-hero-title {
  font-size: 30px;
  letter-spacing: 8px;
  color: var(--gold);
}

.ornament {
  font-size: 20px;
  color: var(--gold);
  opacity: 0.4;
  margin-bottom: 16px;
  letter-spacing: 16px;
}

.sutra-title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-weight: 900;
  font-size: 36px;
  letter-spacing: 12px;
  color: var(--text-primary);
  margin: 0 0 16px;
  line-height: 1.8;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 2px;
}

.sutra-title ruby { margin-right: 6px; }

.sutra-subtitle {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-weight: 500;
  font-size: 22px;
  letter-spacing: 8px;
  color: var(--text-primary);
  margin: 0 0 16px;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  opacity: 0.9;
}

.sutra-subtitle ruby { margin-right: 4px; }

.sutra-title rt, .sutra-subtitle rt {
  font-family: var(--font-pinyin);
  font-size: 13px;
  font-weight: 400;
  color: var(--text-primary);
  opacity: 0.85;
  padding-bottom: 2px;
  letter-spacing: 0;
}

.sutra-author {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 15px;
  color: var(--text-muted);
  letter-spacing: 4px;
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 2px;
}

.sutra-author ruby { margin-right: 2px; }

.sutra-author rt {
  font-family: var(--font-pinyin);
  font-size: 10px;
  color: var(--text-muted);
  opacity: 1;
  padding-bottom: 2px;
  letter-spacing: 0;
}

.divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 32px;
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
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 640px) {
  .sutra-title { font-size: 26px; letter-spacing: 6px; }
  .sutra-subtitle { font-size: 18px; letter-spacing: 4px; }
  .sutra-header { padding: 40px 16px 28px; }
}
</style>
