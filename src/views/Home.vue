<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import catalog from '../data/catalog.json'
import { useRouter } from 'vue-router'
import SearchModal from '../components/SearchModal.vue'
import ZenAudioStation from '../components/ZenAudioStation.vue'

const router = useRouter()
const lastRead = ref(null)

// 首页双生视界：'reading' (阅卷·藏经) | 'listening' (听诵·禅修)
const activeTab = ref(localStorage.getItem('chanyue_home_tab') || 'reading')
watch(activeTab, (val) => {
  localStorage.setItem('chanyue_home_tab', val)
})

const isSearchOpen = ref(false)

function handleShortcut(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    isSearchOpen.value = true
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleShortcut)
  try {
    const raw = localStorage.getItem('chanyue_last_read')
    if (raw) {
      lastRead.value = JSON.parse(raw)
    }
  } catch (e) {}
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleShortcut)
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
    <!-- 顶部静穆阁标（固定锚定，双生视界切换零跳动） -->
    <header class="home-header">
      <div class="ornament">◈</div>
      <h1 class="title">经 书 阁</h1>

      <!-- 双生视界切换 -->
      <div class="home-tab-switcher">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'reading' }"
          @click="activeTab = 'reading'"
        >
          <span>阅卷</span>
        </button>
        <span class="tab-sep">/</span>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'listening' }"
          @click="activeTab = 'listening'"
        >
          <span>听诵</span>
        </button>
      </div>
    </header>

    <!-- 模式一：静谧经卷名录（独立清雅禅台，分割清晰明朗） -->
    <main v-if="activeTab === 'reading'" class="sutra-list">
      <section 
        v-for="(item, idx) in catalog" 
        :key="item.id" 
        class="sutra-card"
        @click="goToBook(item)"
      >
        <!-- 经名大字 -->
        <h2 class="sutra-name">
          {{ item.name }}
        </h2>

        <!-- 印心要语真言 -->
        <p class="sutra-verse">
          “{{ item.coverText }}”
        </p>

        <!-- 卡片底栏操作指引（统一节律：未读为翻阅入静，读过为自适应续读药丸） -->
        <div class="card-footer-action">
          <div 
            v-if="lastRead && lastRead.bookId === item.id" 
            class="resume-pill"
            :title="`续读至：${lastRead.chapterTitle}`"
          >
            <span class="pill-prefix">续读</span>
            <span class="pill-sep">·</span>
            <span class="pill-title">{{ lastRead.chapterTitle }}</span>
            <span class="pill-arrow">→</span>
          </div>
          <div v-else class="card-action-bar">
            <span class="action-text">翻阅入静</span>
            <span class="action-arrow">→</span>
          </div>
        </div>
      </section>

      <!-- 底部索经微触点（动作语义：统一放大镜图标，精准亲密性） -->
      <div class="home-search-seal-wrap">
        <button class="home-search-seal" @click="isSearchOpen = true" title="跨经全文检索 (Cmd/Ctrl+K)">
          <svg class="seal-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span class="seal-text">索 经</span>
        </button>
      </div>
    </main>

    <!-- 模式二：独立禅听修持随身听 -->
    <main v-else class="zen-station-area">
      <ZenAudioStation />
    </main>

    <!-- 底部清净小记 -->
    <footer class="home-footer">
      <p>息妄显真 · 随缘自适</p>
    </footer>

    <!-- 全藏索经弹窗 -->
    <SearchModal v-model:visible="isSearchOpen" />
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  padding: 36px 20px calc(40px + env(safe-area-inset-bottom, 0px));
  max-width: 580px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 顶部阁标（固定锚定，双生视界切换零晃动） */
.home-header {
  text-align: center;
  margin-bottom: 24px;
  width: 100%;
  animation: fadeIn 1.2s ease both;
}

.ornament {
  font-size: 14px;
  color: var(--gold);
  opacity: 0.65;
  margin-bottom: 8px;
  letter-spacing: 6px;
}

.title {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 28px;
  color: var(--text-primary);
  margin: 0 0 16px;
  letter-spacing: 9px;
  font-weight: 700;
  text-shadow: 0 0 24px rgba(212, 165, 116, 0.15);
}

/* 顶部双生视界切换开关 */
.home-tab-switcher {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 4px 14px;
  border-radius: 9999px;
  background: rgba(22, 22, 28, 0.45);
  border: 1px solid rgba(212, 165, 116, 0.16);
  backdrop-filter: blur(8px);
}

.tab-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
  font-size: 12.5px;
  letter-spacing: 2px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 9999px;
  position: relative;
  transition: all 0.25s ease;
}

.tab-btn:active {
  transform: scale(0.95);
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--gold);
  font-weight: 600;
  text-shadow: 0 0 12px rgba(212, 165, 116, 0.4);
}

.tab-sep {
  color: rgba(212, 165, 116, 0.25);
  font-size: 11px;
}

/* 底部索经微触点（精准亲密性与动作语义） */
.home-search-seal-wrap {
  display: flex;
  justify-content: center;
  margin: 20px 0 28px;
}

.home-search-seal {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 20px;
  border-radius: 9999px;
  background: rgba(22, 22, 28, 0.65);
  border: 1px solid rgba(212, 165, 116, 0.22);
  color: var(--gold);
  font-family: 'Noto Serif SC', serif;
  font-size: 12.5px;
  letter-spacing: 2.5px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
}

.home-search-seal:hover {
  background: rgba(212, 165, 116, 0.14);
  border-color: rgba(212, 165, 116, 0.55);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(212, 165, 116, 0.18);
}

.seal-action-icon {
  opacity: 0.85;
  color: var(--gold);
  flex-shrink: 0;
}

.seal-text {
  font-weight: 500;
}

/* 经卷卡片列表（独立禅境展台） */
.sutra-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.zen-station-area {
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

.sutra-card:active {
  transform: scale(0.985);
  background: rgba(22, 22, 28, 0.7);
  transition: transform 0.15s cubic-bezier(0.32, 0.72, 0, 1);
}

/* 经名：典雅修长的宋体大字 */
.sutra-name {
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 23px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 4px 0 10px;
  letter-spacing: 4px;
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

/* 卡片底栏操作区（统一定高节律，杜绝卡片高度失衡） */
.card-footer-action {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 28px;
}

/* 续读药丸胶囊（UI/UX Pro Max 紧凑自适应标准：单行防折、弹性截断、消除多余红点杂质） */
.resume-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: min(100%, 340px);
  padding: 4.5px 14px;
  border-radius: 9999px;
  background: rgba(212, 165, 116, 0.09);
  border: 1px solid rgba(212, 165, 116, 0.28);
  font-family: 'Noto Serif SC', serif;
  font-size: 11.5px;
  color: var(--gold);
  letter-spacing: 0.6px;
  box-sizing: border-box;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  transition: all 0.3s cubic-bezier(0.32, 0.72, 0, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.sutra-card:hover .resume-pill {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(212, 165, 116, 0.15);
}

.pill-prefix {
  flex-shrink: 0;
  font-weight: 500;
  opacity: 0.9;
}

.pill-sep {
  flex-shrink: 0;
  margin: 0 5px;
  opacity: 0.45;
}

.pill-title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.95;
}

.pill-arrow {
  flex-shrink: 0;
  margin-left: 5px;
  transition: transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
  opacity: 0.85;
}

.sutra-card:hover .pill-arrow {
  transform: translateX(3px);
  opacity: 1;
}

/* 翻阅入静指引 */
.card-action-bar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'Noto Serif SC', serif;
  font-size: 11.5px;
  color: var(--gold);
  letter-spacing: 2px;
  opacity: 0.72;
  transition: all 0.3s ease;
  padding: 4px 0;
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

.home-footer {
  text-align: center;
  margin-top: 36px;
  font-family: 'Noto Serif SC', 'KaiTi', serif;
  font-size: 12px;
  color: var(--text-muted);
  opacity: 0.75;
  letter-spacing: 3px;
  display: flex;
  justify-content: center;
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
