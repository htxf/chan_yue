<script setup>
import { ref, onMounted } from 'vue'
import catalog from '../data/catalog.json'
import { useRouter } from 'vue-router'

const router = useRouter()
const lastRead = ref(null)

onMounted(() => {
  try {
    const raw = localStorage.getItem('chanyue_last_read')
    if (raw) {
      lastRead.value = JSON.parse(raw)
    }
  } catch (e) {}
})

function goToBook(item) {
  if (lastRead.value && lastRead.value.bookId === item.id) {
    router.push(`/${item.id}/${lastRead.value.chapterId || 'chapter_1'}`)
  } else {
    router.push(`/${item.id}/chapter_1`)
  }
}
</script>

<template>
  <div class="home-container">
    <!-- 顶部静穆阁标 -->
    <header class="home-header">
      <div class="ornament">◈</div>
      <h1 class="title">经 书 阁</h1>
      <p class="subtitle">禅思无界 · 阅心有道</p>
    </header>

    <!-- 静谧经卷名录（文人墨意 · 空灵留白） -->
    <main class="sutra-list">
      <div 
        v-for="(item, idx) in catalog" 
        :key="item.id" 
        class="sutra-entry-wrap"
      >
        <section 
          class="sutra-entry" 
          @click="goToBook(item)"
        >
          <!-- 经名大字 -->
          <h2 class="sutra-name">
            {{ item.name }}
          </h2>

          <!-- 印心要语真言 -->
          <p class="sutra-verse">
            {{ item.coverText }}
          </p>

          <!-- 续读指引（静谧内嵌，无需巨大横幅） -->
          <div 
            v-if="lastRead && lastRead.bookId === item.id" 
            class="resume-whisper"
          >
            <span class="whisper-dot">●</span>
            <span>上次持诵至 {{ lastRead.chapterTitle }}</span>
            <span class="whisper-arrow">· 继续持诵 →</span>
          </div>

          <!-- 悬浮进入微光 -->
          <div class="entry-enter-hint">
            <span>翻阅入静</span>
            <span class="hint-arrow">→</span>
          </div>
        </section>

        <!-- 经卷间雅致微点断隔 -->
        <div v-if="idx < catalog.length - 1" class="entry-divider">
          <span class="divider-line"></span>
          <span class="divider-gem">◈</span>
          <span class="divider-line"></span>
        </div>
      </div>
    </main>

    <!-- 底部清净小记 -->
    <footer class="home-footer">
      <p>息妄显真 · 随缘自适</p>
    </footer>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 48px 24px 60px;
  max-width: 580px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* 顶部阁标 */
.home-header {
  text-align: center;
  margin-bottom: 40px;
  animation: fadeIn 1.2s ease both;
}

.ornament {
  font-size: 16px;
  color: var(--gold);
  opacity: 0.6;
  margin-bottom: 8px;
  letter-spacing: 12px;
}

.title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 30px;
  color: var(--text-primary);
  margin: 0 0 10px;
  letter-spacing: 10px;
  font-weight: 700;
  text-shadow: 0 0 24px rgba(212, 165, 116, 0.15);
}

.subtitle {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  font-size: 14px;
  letter-spacing: 5px;
  margin: 0;
  opacity: 0.8;
}

/* 经卷名录 */
.sutra-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.sutra-entry-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 单部经卷纯净交互区 */
.sutra-entry {
  width: 100%;
  text-align: center;
  padding: 28px 20px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  background: transparent;
}

.sutra-entry:hover {
  background: rgba(212, 165, 116, 0.03);
}

/* 经名：典雅修长的宋体大字，带自然字距 */
.sutra-name {
  margin: 0 0 14px;
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 24px;
  font-weight: 700;
  color: #e8e2d8;
  letter-spacing: 6px;
  transition: all 0.35s ease;
  line-height: 1.5;
}

.sutra-entry:hover .sutra-name {
  color: var(--gold);
  text-shadow: 0 0 18px rgba(212, 165, 116, 0.65), 0 0 36px rgba(212, 165, 116, 0.25);
  transform: translateY(-2px);
}

/* 印心真言名句 */
.sutra-verse {
  margin: 0;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--gold-dim);
  font-size: 15px;
  letter-spacing: 3px;
  line-height: 1.6;
  opacity: 0.85;
  transition: color 0.3s ease;
}

.sutra-entry:hover .sutra-verse {
  color: var(--gold);
  opacity: 1;
}

/* 续读低语（极其克制融入） */
.resume-whisper {
  margin-top: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  color: var(--gold);
  opacity: 0.8;
  letter-spacing: 1px;
  padding: 4px 14px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.2);
  transition: all 0.25s ease;
}

.sutra-entry:hover .resume-whisper {
  opacity: 1;
  background: rgba(212, 165, 116, 0.16);
  border-color: rgba(212, 165, 116, 0.4);
}

.whisper-dot {
  font-size: 8px;
  color: #c94a38;
  opacity: 0.9;
}

.whisper-arrow {
  color: var(--gold);
  font-weight: 500;
}

/* 进入提示微光 */
.entry-enter-hint {
  margin-top: 16px;
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 3px;
  opacity: 0;
  transform: translateY(4px);
  transition: all 0.35s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.sutra-entry:hover .entry-enter-hint {
  opacity: 0.6;
  color: var(--gold);
  transform: translateY(0);
}

/* 经卷断隔金线 */
.entry-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  width: 100%;
  max-width: 280px;
  margin: 16px 0;
  opacity: 0.35;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.6), transparent);
}

.divider-gem {
  font-size: 10px;
  color: var(--gold);
  letter-spacing: 0;
}

/* 底部清净字 */
.home-footer {
  text-align: center;
  margin-top: 40px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 12px;
  color: var(--text-muted);
  opacity: 0.35;
  letter-spacing: 4px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 640px) {
  .home-container {
    padding: 36px 20px 48px;
  }
  .home-header {
    margin-bottom: 28px;
  }
  .title {
    font-size: 26px;
    letter-spacing: 8px;
  }
  .sutra-name {
    font-size: 21px;
    letter-spacing: 4px;
  }
  .sutra-verse {
    font-size: 14px;
    letter-spacing: 2px;
  }
  .sutra-entry {
    padding: 22px 16px;
  }
  .entry-enter-hint {
    display: none;
  }
}
</style>
