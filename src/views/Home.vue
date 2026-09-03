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

function goToReader(id, chapterId = 'chapter_1') {
  router.push(`/${id}/${chapterId}`)
}
</script>

<template>
  <div class="home-container">
    <header class="home-header">
      <div class="ornament">◈</div>
      <h1 class="title">经 书 阁</h1>
      <p class="subtitle">禅思无界 · 阅心有道</p>
    </header>

    <!-- 续读浮舟 (Resume Reading Banner) -->
    <div 
      v-if="lastRead" 
      class="resume-banner"
      @click="goToReader(lastRead.bookId, lastRead.chapterId)"
    >
      <div class="resume-left">
        <div class="resume-icon-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="resume-icon" width="16" height="16">
            <path d="M12 3a9 9 0 0 0-9 9c0 4.97 4.03 9 9 9s9-4.03 9-9a9 9 0 0 0-9-9z" opacity="0.3"/>
            <path d="M12 7c-2 2.5-3 5-3 7a3 3 0 0 0 6 0c0-2-1-4.5-3-7z"/>
          </svg>
        </div>
        <div class="resume-info">
          <span class="resume-tag">继续昨日持诵</span>
          <h3 class="resume-title">《{{ lastRead.bookTitle }}》· {{ lastRead.chapterTitle }}</h3>
        </div>
      </div>
      <div class="resume-btn">
        <span>接续</span>
        <span class="btn-arrow">→</span>
      </div>
    </div>

    <!-- 古籍藏经卡片流 -->
    <div class="catalog-grid">
      <div 
        v-for="(item, idx) in catalog" 
        :key="item.id" 
        class="book-card"
        @click="goToReader(item.id)"
      >
        <!-- 线装书脊与暗金缝线 -->
        <div class="book-spine">
          <span class="stitch"></span>
          <span class="stitch"></span>
          <span class="stitch"></span>
          <span class="stitch"></span>
        </div>

        <div class="card-body">
          <div class="card-main">
            <!-- 竖排宣纸题签条 -->
            <div class="title-strip">
              <span class="strip-text">{{ item.name }}</span>
            </div>

            <!-- 书籍信息与名句 -->
            <div class="book-meta-box">
              <div class="meta-top">
                <span class="edition-badge">
                  {{ item.id === 'jingangjing' ? '三十二分全 · 1~8品双音色' : '全文纯享 · 沉浸双音色' }}
                </span>
                <span class="seal-stamp">◈ 藏经</span>
              </div>
              
              <blockquote class="book-cover-quote">
                “{{ item.coverText }}”
              </blockquote>
            </div>
          </div>

          <div class="card-footer">
            <span class="read-btn">翻阅持诵</span>
            <span class="arrow">→</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 60px 20px 80px;
  max-width: 760px;
  margin: 0 auto;
}

.home-header {
  text-align: center;
  margin-bottom: 40px;
  animation: fadeIn 1s ease both;
}

.ornament {
  font-size: 20px;
  color: var(--gold);
  opacity: 0.5;
  margin-bottom: 16px;
  letter-spacing: 12px;
}

.title {
  font-family: 'Noto Serif SC', serif;
  font-size: 32px;
  color: var(--text-primary);
  margin: 0 0 10px;
  letter-spacing: 8px;
  font-weight: 900;
}

.subtitle {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  font-size: 15px;
  letter-spacing: 4px;
}

/* ===== 续读浮舟 (Resume Banner) ===== */
.resume-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 36px;
  padding: 14px 20px;
  background: rgba(212, 165, 116, 0.05);
  border: 1px solid rgba(212, 165, 116, 0.2);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.45);
  animation: slideUp 0.6s ease backwards;
}

.resume-banner:hover {
  background: rgba(212, 165, 116, 0.1);
  border-color: rgba(212, 165, 116, 0.4);
  transform: translateY(-2px);
}

.resume-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.resume-icon-box {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gold);
}

.resume-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.resume-tag {
  font-size: 11px;
  color: var(--gold-muted);
  letter-spacing: 1px;
}

.resume-title {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  font-weight: 600;
  letter-spacing: 1px;
}

.resume-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--gold);
  padding: 4px 12px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.25);
  font-family: 'Noto Serif SC', serif;
  transition: all 0.2s;
}

.resume-banner:hover .btn-arrow {
  transform: translateX(3px);
}

.btn-arrow {
  transition: transform 0.2s;
}

/* ===== 古籍卡片列表 ===== */
.catalog-grid {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.book-card {
  display: flex;
  background: rgba(18, 18, 26, 0.7);
  border: 1px solid rgba(212, 165, 116, 0.15);
  border-radius: 16px;
  padding: 0;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px);
  box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.8s ease backwards;
}

.book-card:nth-child(1) { animation-delay: 0.1s; }
.book-card:nth-child(2) { animation-delay: 0.2s; }

.book-card:hover {
  transform: translateY(-4px);
  border-color: rgba(212, 165, 116, 0.4);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.7), 0 0 24px rgba(212, 165, 116, 0.08);
}

/* 线装书脊微缝线 */
.book-spine {
  width: 24px;
  background: rgba(212, 165, 116, 0.03);
  border-right: 1px dashed rgba(212, 165, 116, 0.2);
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  align-items: center;
  padding: 24px 0;
  flex-shrink: 0;
}

.stitch {
  width: 2px;
  height: 12px;
  background: rgba(212, 165, 116, 0.3);
  border-radius: 1px;
}

.card-body {
  flex: 1;
  padding: 26px 28px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-main {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

/* 竖排白宣题签 */
.title-strip {
  writing-mode: vertical-rl;
  text-orientation: upright;
  background: #f4eee3;
  color: #1a1612;
  border: 1px solid #c9bda8;
  border-radius: 4px;
  padding: 12px 6px;
  font-family: 'Noto Serif SC', serif;
  font-weight: 900;
  font-size: 15px;
  letter-spacing: 3px;
  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.35);
  flex-shrink: 0;
}

.book-meta-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.edition-badge {
  font-size: 11px;
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.25);
  padding: 2px 8px;
  border-radius: 9999px;
  letter-spacing: 1px;
}

.seal-stamp {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 11px;
  color: #c94a38;
  border: 1px solid #c94a38;
  padding: 1px 6px;
  border-radius: 3px;
  letter-spacing: 1px;
  opacity: 0.85;
}

.book-cover-quote {
  margin: 0;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.6;
  letter-spacing: 2px;
}

.card-footer {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid rgba(212, 165, 116, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.read-btn {
  color: var(--gold);
  font-size: 13px;
  letter-spacing: 3px;
  font-family: 'Noto Serif SC', serif;
  opacity: 0.85;
  transition: opacity 0.3s ease;
}

.arrow {
  color: var(--gold);
  opacity: 0.4;
  transform: translateX(-6px);
  transition: all 0.3s ease;
}

.book-card:hover .read-btn {
  opacity: 1;
}

.book-card:hover .arrow {
  opacity: 1;
  transform: translateX(0);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .home-container {
    padding: 36px 14px 60px;
  }
  .card-body {
    padding: 20px 18px;
  }
  .card-main {
    gap: 16px;
  }
  .title-strip {
    font-size: 13px;
    padding: 10px 5px;
  }
  .book-cover-quote {
    font-size: 13px;
  }
}
</style>
