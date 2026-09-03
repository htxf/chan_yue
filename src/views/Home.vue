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

    <!-- 静谧经卷名录（独立清雅禅台，分割清晰明朗） -->
    <main class="sutra-list">
      <section 
        v-for="(item, idx) in catalog" 
        :key="item.id" 
        class="sutra-card"
        @click="goToBook(item)"
      >
        <!-- 卷次眉标 -->
        <div class="card-meta-top">
          <span class="meta-ornament">◈</span>
          <span class="meta-vol">卷{{ idx === 0 ? '一' : '二' }}</span>
          <span class="meta-sep">·</span>
          <span class="meta-tag">{{ item.id === 'jingangjing' ? '三十二分全' : '全文纯享' }}</span>
        </div>

        <!-- 经名大字 -->
        <h2 class="sutra-name">
          {{ item.name }}
        </h2>

        <!-- 印心要语真言 -->
        <p class="sutra-verse">
          “{{ item.coverText }}”
        </p>

        <!-- 续读指引（静谧内嵌） -->
        <div 
          v-if="lastRead && lastRead.bookId === item.id" 
          class="resume-whisper"
        >
          <span class="whisper-dot">●</span>
          <span>上次持诵至 {{ lastRead.chapterTitle }}</span>
          <span class="whisper-arrow">· 继续持诵 →</span>
        </div>

        <!-- 卡片底栏微光入静指引 -->
        <div class="card-action-bar">
          <span class="action-text">翻阅入静</span>
          <span class="action-arrow">→</span>
        </div>
      </section>
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
  padding: 40px 20px 48px;
  max-width: 580px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* 顶部阁标 */
.home-header {
  text-align: center;
  margin-bottom: 28px;
  animation: fadeIn 1.2s ease both;
}

.ornament {
  font-size: 15px;
  color: var(--gold);
  opacity: 0.6;
  margin-bottom: 6px;
  letter-spacing: 10px;
}

.title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 28px;
  color: var(--text-primary);
  margin: 0 0 8px;
  letter-spacing: 9px;
  font-weight: 700;
  text-shadow: 0 0 24px rgba(212, 165, 116, 0.15);
}

.subtitle {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  font-size: 13px;
  letter-spacing: 4px;
  margin: 0;
  opacity: 0.8;
}

/* 经卷卡片列表（独立禅境展台） */
.sutra-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

/* 单部经卷独立卡片（清晰边界，温润通透） */
.sutra-card {
  width: 100%;
  text-align: center;
  padding: 24px 20px;
  border-radius: 18px;
  background: rgba(22, 22, 28, 0.55);
  border: 1px solid rgba(212, 165, 116, 0.16);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.sutra-card:hover {
  background: rgba(26, 26, 34, 0.75);
  border-color: rgba(212, 165, 116, 0.42);
  transform: translateY(-2px);
  box-shadow: 0 12px 28px -4px rgba(0, 0, 0, 0.6), 0 0 24px rgba(212, 165, 116, 0.08);
}

/* 卷次眉标（明确部次划分） */
.card-meta-top {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'Noto Serif SC', serif;
  font-size: 11px;
  color: var(--gold);
  opacity: 0.9;
  letter-spacing: 1px;
  margin-bottom: 12px;
}

.meta-ornament {
  font-size: 9px;
  opacity: 0.75;
}

.meta-sep {
  opacity: 0.45;
}

.meta-tag {
  color: var(--text-muted);
  opacity: 0.95;
}

/* 经名：典雅修长的宋体大字 */
.sutra-name {
  margin: 0 0 10px;
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 23px;
  font-weight: 700;
  color: #f2ece2;
  letter-spacing: 6px;
  transition: all 0.3s ease;
  line-height: 1.4;
}

.sutra-card:hover .sutra-name {
  color: var(--gold);
  text-shadow: 0 0 18px rgba(212, 165, 116, 0.65);
}

/* 印心真言名句（泥金微光，清晰舒雅） */
.sutra-verse {
  margin: 0;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--gold-dim);
  font-size: 14.5px;
  letter-spacing: 2.5px;
  line-height: 1.5;
  opacity: 0.95;
  transition: color 0.3s ease;
}

.sutra-card:hover .sutra-verse {
  color: var(--gold);
  opacity: 1;
}

/* 续读低语（内嵌精致胶囊） */
.resume-whisper {
  margin-top: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  color: var(--gold);
  opacity: 0.95;
  letter-spacing: 0.8px;
  padding: 4px 14px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.28);
  transition: all 0.25s ease;
}

.sutra-card:hover .resume-whisper {
  background: rgba(212, 165, 116, 0.2);
  border-color: rgba(212, 165, 116, 0.5);
}

.whisper-dot {
  font-size: 8px;
  color: #d95340;
  opacity: 0.95;
}

.whisper-arrow {
  color: var(--gold);
  font-weight: 500;
}

/* 翻阅入静指引 */
.card-action-bar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: 'Noto Serif SC', serif;
  font-size: 11.5px;
  color: var(--gold);
  letter-spacing: 2px;
  opacity: 0.72;
  transition: all 0.3s ease;
}

.sutra-card:hover .card-action-bar {
  opacity: 1;
}

.sutra-card:hover .action-arrow {
  transform: translateX(3px);
}

.action-arrow {
  transition: transform 0.2s ease;
}

/* 底部清净字 */
.home-footer {
  text-align: center;
  margin-top: 36px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 12px;
  color: var(--text-muted);
  opacity: 0.65;
  letter-spacing: 4px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 640px) {
  .home-container {
    padding: 30px 16px 40px;
  }
  .home-header {
    margin-bottom: 22px;
  }
  .title {
    font-size: 24px;
    letter-spacing: 7px;
  }
  .sutra-name {
    font-size: 20px;
    letter-spacing: 4px;
  }
  .sutra-verse {
    font-size: 13.5px;
    letter-spacing: 1.5px;
  }
  .sutra-card {
    padding: 20px 16px;
  }
  .sutra-list {
    gap: 16px;
  }
}
</style>
