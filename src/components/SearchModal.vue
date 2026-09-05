<!--
  SearchModal - 藏经墨索 / 禅意全文检索浮层
  支持跨经、跨卷全文实时检索，关键词泥金高亮与快速直达
-->
<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import searchIndex from '../data/search_index.json'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['update:visible', 'select'])
const router = useRouter()

const query = ref('')
const searchInput = ref(null)

const suggestions = [
  '诸相非相',
  '照见五蕴皆空',
  '一切有为法',
  '降伏其心',
  '度一切苦厄',
  '应无所住'
]

watch(() => props.visible, (val) => {
  if (val) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  } else {
    query.value = ''
  }
})

function close() {
  emit('update:visible', false)
}

function handleKeydown(e) {
  if (e.key === 'Escape' && props.visible) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

/** 实时过滤匹配结果 */
const searchResults = computed(() => {
  const q = query.value.trim()
  if (!q) return []
  const lowerQ = q.toLowerCase()

  const results = []
  for (const item of searchIndex) {
    const matchedSnippets = []
    for (const s of item.snippets) {
      if (s.toLowerCase().includes(lowerQ)) {
        matchedSnippets.push(s)
      }
    }
    const titleMatch = item.chapterTitle.toLowerCase().includes(lowerQ)
    if (matchedSnippets.length > 0 || titleMatch) {
      results.push({
        bookId: item.bookId,
        bookTitle: item.bookTitle,
        chapterId: item.chapterId,
        chapterTitle: item.chapterTitle,
        snippets: matchedSnippets.slice(0, 3)
      })
    }
  }
  return results
})

function highlightText(text, keyword) {
  if (!keyword || !text) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return text.replace(regex, '<mark class="search-mark">$1</mark>')
}

function selectResult(res, snippet = '') {
  close()
  emit('select', { ...res, snippet })
  router.push({
    name: 'Reader',
    params: {
      bookId: res.bookId,
      chapterId: res.chapterId
    },
    query: snippet ? { hl: snippet.slice(0, 10) } : {}
  })
}
</script>

<template>
  <Teleport to="body">
    <transition name="search-fade">
      <div v-if="visible" class="search-backdrop" @click="close">
        <div class="search-dialog" @click.stop>
          <!-- 搜索输入区 -->
          <div class="search-input-wrapper">
            <span class="search-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="18" height="18">
                <circle cx="11" cy="11" r="7"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </span>
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              class="search-input"
              placeholder="索经揽要... 试寻“诸相、五蕴、应无所住”"
              maxlength="40"
            />
            <button v-if="query" class="clear-btn" @click="query = ''">×</button>
            <button class="modal-close-btn" @click="close" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- 灵犀微荐 -->
          <div v-if="!query" class="suggestion-box">
            <span class="sug-label">拈香寻句：</span>
            <div class="sug-tags">
              <button
                v-for="s in suggestions"
                :key="s"
                class="sug-chip"
                @click="query = s"
              >
                {{ s }}
              </button>
            </div>
          </div>

          <!-- 搜索结果列表 -->
          <div class="search-body">
            <div v-if="query && searchResults.length === 0" class="no-results">
              <p>未探得与“{{ query }}”相合之经句</p>
              <span class="empty-sub">万法皆空 · 亦可探寻其他字句</span>
            </div>

            <div v-else-if="query" class="results-list">
              <div
                v-for="(res, idx) in searchResults"
                :key="`${res.bookId}-${res.chapterId}-${idx}`"
                class="result-card"
                @click="selectResult(res, res.snippets[0])"
              >
                <div class="card-header">
                  <span class="book-pill">{{ res.bookTitle }}</span>
                  <span class="ch-name" v-html="highlightText(res.chapterTitle, query)"></span>
                </div>
                <div v-if="res.snippets.length" class="snippets-box">
                  <div
                    v-for="(s, sIdx) in res.snippets"
                    :key="sIdx"
                    class="snippet-line"
                    v-html="highlightText(s, query)"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部微注 -->
          <div class="search-footer">
            <span>经藏墨索 · 探寻般若法音</span>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.search-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: rgba(8, 8, 12, 0.78);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 80px 20px 20px;
}

.search-dialog {
  width: 100%;
  max-width: 580px;
  background: rgba(22, 22, 28, 0.94);
  border: 1px solid rgba(212, 165, 116, 0.28);
  border-radius: 20px;
  box-shadow: 0 16px 40px -8px rgba(0, 0, 0, 0.8), 0 0 32px rgba(212, 165, 116, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalScale 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.14);
}

.search-icon {
  color: var(--gold);
  opacity: 0.85;
  display: flex;
  align-items: center;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-family: 'Noto Serif SC', 'SimSun', serif;
  font-size: 16px;
  color: var(--text-primary);
  letter-spacing: 1.5px;
}

.search-input::placeholder {
  color: var(--text-muted);
  opacity: 0.75;
  font-size: 14px;
}

.clear-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}

.modal-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
  flex-shrink: 0;
  opacity: 0.75;
}

.modal-close-btn:hover {
  color: var(--gold);
  background: rgba(212, 165, 116, 0.12);
  opacity: 1;
}

.suggestion-box {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sug-label {
  font-size: 12px;
  color: var(--gold);
  opacity: 0.8;
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 1px;
}

.sug-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sug-chip {
  background: rgba(212, 165, 116, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.18);
  border-radius: 9999px;
  padding: 4px 12px;
  font-size: 12.5px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.sug-chip:hover {
  background: rgba(212, 165, 116, 0.16);
  border-color: rgba(212, 165, 116, 0.4);
  color: var(--gold);
  transform: translateY(-1px);
}

.search-body {
  max-height: 52vh;
  overflow-y: auto;
  padding: 8px 12px 14px;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-family: 'Noto Serif SC', serif;
}

.empty-sub {
  font-size: 12px;
  opacity: 0.65;
  display: block;
  margin-top: 6px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-card {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(212, 165, 116, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.result-card:hover {
  background: rgba(212, 165, 116, 0.08);
  border-color: rgba(212, 165, 116, 0.35);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.book-pill {
  font-size: 11px;
  font-family: 'Noto Serif SC', serif;
  padding: 1px 8px;
  border-radius: 4px;
  background: rgba(212, 165, 116, 0.12);
  color: var(--gold);
  border: 1px solid rgba(212, 165, 116, 0.25);
}

.ch-name {
  font-size: 14px;
  font-weight: 600;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-primary);
}

.snippets-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 2px;
}

.snippet-line {
  font-size: 13px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-muted);
  line-height: 1.6;
}

:deep(.search-mark) {
  background: transparent;
  color: #ffc470;
  font-weight: 700;
  text-decoration: underline;
  text-decoration-color: rgba(212, 165, 116, 0.5);
  text-underline-offset: 3px;
}

.search-footer {
  padding: 10px 20px;
  border-top: 1px solid rgba(212, 165, 116, 0.1);
  text-align: center;
  font-size: 11px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text-muted);
  opacity: 0.65;
  letter-spacing: 2px;
}

@keyframes modalScale {
  from { opacity: 0; transform: scale(0.96) translateY(-8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.search-fade-enter-active,
.search-fade-leave-active {
  transition: opacity 0.25s ease;
}

.search-fade-enter-from,
.search-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .search-backdrop {
    padding: 30px 14px 14px;
  }
  .search-input-wrapper {
    padding: 12px 14px;
  }
  .search-input {
    font-size: 14.5px;
  }
}
</style>
