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
    <!-- 顶部紧凑禅意阁标 -->
    <header class="home-header">
      <div class="ornament">◈</div>
      <h1 class="title">经 书 阁</h1>
      <p class="subtitle">禅思无界 · 阅心有道</p>
    </header>

    <!-- 续读浮舟 (极简微缩接续条) -->
    <div 
      v-if="lastRead" 
      class="resume-banner"
      @click="goToReader(lastRead.bookId, lastRead.chapterId)"
    >
      <div class="resume-left">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="resume-icon" width="14" height="14">
          <path d="M12 3a9 9 0 0 0-9 9c0 4.97 4.03 9 9 9s9-4.03 9-9a9 9 0 0 0-9-9z" opacity="0.3"/>
          <path d="M12 7c-2 2.5-3 5-3 7a3 3 0 0 0 6 0c0-2-1-4.5-3-7z"/>
        </svg>
        <span class="resume-tag">接续持诵</span>
        <span class="resume-divider">·</span>
        <h3 class="resume-title">《{{ lastRead.bookTitle }}》{{ lastRead.chapterTitle }}</h3>
      </div>
      <div class="resume-action">
        <span>进入</span>
        <span class="action-arrow">→</span>
      </div>
    </div>

    <!-- 古雅紧凑经册列表 (首屏完全收纳，不遮挡、不截断) -->
    <div class="catalog-grid">
      <div 
        v-for="(item, idx) in catalog" 
        :key="item.id" 
        class="book-card"
        @click="goToReader(item.id)"
      >
        <!-- 左侧：微缩线装古经册封面封皮 (Antique Sutra Tome) -->
        <div class="tome-cover">
          <div class="tome-spine">
            <span class="tome-stitch"></span>
            <span class="tome-stitch"></span>
            <span class="tome-stitch"></span>
            <span class="tome-stitch"></span>
          </div>
          <div class="tome-label">
            <span>{{ item.name }}</span>
          </div>
        </div>

        <!-- 右侧：经卷提要与持诵导流 -->
        <div class="card-content">
          <div class="content-header">
            <div class="title-group">
              <h2 class="book-title">{{ item.name }}</h2>
              <span class="seal-mark">◈ 藏经</span>
            </div>
            <span class="edition-tag">
              {{ item.id === 'jingangjing' ? '32分全 · 双音色' : '全文纯享 · 双音色' }}
            </span>
          </div>

          <!-- 核心法要名句 -->
          <p class="book-verse">
            “{{ item.coverText }}”
          </p>

          <!-- 底栏修持指引 -->
          <div class="card-bottom">
            <span class="scroll-tag">卷之{{ idx === 0 ? '上' : '下' }} · 鸠摩罗什/玄奘译</span>
            <div class="action-link">
              <span>翻阅持诵</span>
              <span class="action-arrow">→</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 32px 18px 48px;
  max-width: 620px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

/* 顶部阁标紧凑收敛 */
.home-header {
  text-align: center;
  margin-bottom: 20px;
  animation: fadeIn 0.8s ease both;
}

.ornament {
  font-size: 13px;
  color: var(--gold);
  opacity: 0.55;
  margin-bottom: 4px;
  letter-spacing: 8px;
}

.title {
  font-family: 'Noto Serif SC', serif;
  font-size: 25px;
  color: var(--text-primary);
  margin: 0 0 5px;
  letter-spacing: 7px;
  font-weight: 900;
}

.subtitle {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--text-muted);
  font-size: 13px;
  letter-spacing: 3px;
}

/* ===== 极简微缩续读浮舟 ===== */
.resume-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  padding: 10px 16px;
  background: rgba(212, 165, 116, 0.05);
  border: 1px solid rgba(212, 165, 116, 0.22);
  border-radius: 12px;
  backdrop-filter: blur(20px);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.45);
  animation: slideUp 0.5s ease backwards;
}

.resume-banner:hover {
  background: rgba(212, 165, 116, 0.1);
  border-color: rgba(212, 165, 116, 0.45);
  transform: translateY(-1px);
}

.resume-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.resume-icon {
  color: var(--gold);
  flex-shrink: 0;
}

.resume-tag {
  font-size: 11.5px;
  color: var(--gold);
  letter-spacing: 0.5px;
  white-space: nowrap;
  flex-shrink: 0;
}

.resume-divider {
  color: var(--gold-muted);
  opacity: 0.4;
  font-size: 11px;
}

.resume-title {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-primary);
  font-family: 'Noto Serif SC', serif;
  font-weight: 500;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.resume-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--gold);
  padding: 4px 12px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.28);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 1px;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.resume-banner:hover .resume-action {
  background: rgba(212, 165, 116, 0.2);
  border-color: var(--gold);
}

.resume-banner:hover .action-arrow {
  transform: translateX(3px);
}

.action-arrow {
  transition: transform 0.2s ease;
}

/* ===== 紧凑古雅经册卡片 ===== */
.catalog-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.book-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(18, 18, 26, 0.72);
  border: 1px solid rgba(212, 165, 116, 0.18);
  border-radius: 14px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.6s ease backwards;
}

.book-card:nth-child(1) { animation-delay: 0.1s; }
.book-card:nth-child(2) { animation-delay: 0.2s; }

.book-card:hover {
  transform: translateY(-3px);
  border-color: rgba(212, 165, 116, 0.45);
  box-shadow: 0 14px 30px -6px rgba(0, 0, 0, 0.7), 0 0 20px rgba(212, 165, 116, 0.08);
}

/* 左侧：微缩线装古籍封面 (Mini Tome Cover) */
.tome-cover {
  width: 76px;
  height: 104px;
  background: #15141a;
  border: 1px solid rgba(212, 165, 116, 0.3);
  border-radius: 5px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 3px 4px 14px rgba(0, 0, 0, 0.65);
}

.tome-spine {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 14px;
  border-right: 1px dashed rgba(212, 165, 116, 0.28);
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  align-items: center;
  padding: 6px 0;
}

.tome-stitch {
  width: 1.5px;
  height: 8px;
  background: rgba(212, 165, 116, 0.4);
  border-radius: 1px;
}

.tome-label {
  writing-mode: vertical-rl;
  text-orientation: upright;
  background: #f5efe6;
  color: #1a1612;
  border: 1px solid #c8bba6;
  border-radius: 2px;
  padding: 6px 3px;
  font-family: 'Noto Serif SC', serif;
  font-weight: 900;
  font-size: 10.5px;
  letter-spacing: 2px;
  margin-left: 10px;
  box-shadow: 1px 1px 4px rgba(0, 0, 0, 0.45);
}

/* 右侧内容区域 */
.card-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.book-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 15.5px;
  color: var(--text-primary);
  letter-spacing: 1px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.seal-mark {
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 9.5px;
  color: #c94a38;
  border: 1px solid #c94a38;
  padding: 1px 4px;
  border-radius: 2px;
  letter-spacing: 0.5px;
  opacity: 0.85;
  flex-shrink: 0;
}

.edition-tag {
  font-size: 10px;
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.25);
  padding: 2px 7px;
  border-radius: 9999px;
  letter-spacing: 0.5px;
  white-space: nowrap;
  flex-shrink: 0;
}

.book-verse {
  margin: 0;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  color: var(--gold);
  font-size: 13px;
  line-height: 1.5;
  letter-spacing: 1.5px;
  opacity: 0.92;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 2px;
  padding-top: 6px;
  border-top: 1px solid rgba(212, 165, 116, 0.08);
}

.scroll-tag {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.65;
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--gold);
  font-size: 12px;
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 1.5px;
  opacity: 0.82;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.book-card:hover .action-link {
  opacity: 1;
}

.book-card:hover .action-arrow {
  transform: translateX(3px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .home-container {
    padding: 24px 14px 40px;
  }
  .title {
    font-size: 22px;
    letter-spacing: 6px;
  }
  .tome-cover {
    width: 68px;
    height: 94px;
  }
  .tome-label {
    font-size: 9.5px;
  }
  .book-title {
    font-size: 14.5px;
  }
  .book-verse {
    font-size: 12.5px;
  }
}
</style>
