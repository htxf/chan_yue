<!--
  SutraBody - 经文段落容器
  承载所有段落的滚动区域
-->
<script setup>
import SutraParagraph from './SutraParagraph.vue'

defineProps({
  paragraphs: Array,
  currentParagraphId: Number,
  currentTime: { type: Number, default: 0 },
  mode: String,
})
</script>

<template>
  <div class="sutra-body">
    <SutraParagraph
      v-for="(p, i) in paragraphs"
      :key="p.id ?? i"
      :paragraph="p"
      :active="(p.id ?? (i + 1)) === currentParagraphId"
      :index="i"
      :currentTime="currentTime"
      :mode="mode"
    />
    
    <slot name="footer"></slot>
    
    <!-- 底部自适应留白：禅听模式预留播放条96px，纯阅读模式仅留28px -->
    <div class="bottom-spacer" :class="{ 'mode-listening': mode === 'listening' }"></div>
  </div>
</template>

<style scoped>
.sutra-body {
  flex: 1;
  padding: 0 20px 20px;
  width: 100%;
  max-width: 680px;
  margin: 0 auto;
  box-sizing: border-box;
  transition: max-width 0.3s ease, padding 0.3s ease;
}

/* 视口自适应：电脑宽屏（>= 1024px）版心流式舒展至 920px，单行从容容纳 22~24 个汉字 */
@media (min-width: 1024px) {
  .sutra-body {
    width: min(92vw, 920px);
    max-width: 920px;
    padding: 0 32px 32px;
  }
}

/* 超大屏 / 2K 显示器（>= 1440px）：版心舒展至 1020px，单行容纳 24~26 个汉字，黄金留白 */
@media (min-width: 1440px) {
  .sutra-body {
    width: min(90vw, 1020px);
    max-width: 1020px;
    padding: 0 40px 40px;
  }
}

.bottom-spacer {
  height: 28px;
  transition: height 0.35s ease;
}

.bottom-spacer.mode-listening {
  height: 96px;
}

/* 自定义滚动条 */
.sutra-body::-webkit-scrollbar {
  width: 4px;
}
.sutra-body::-webkit-scrollbar-track {
  background: transparent;
}
.sutra-body::-webkit-scrollbar-thumb {
  background: rgba(212, 165, 116, 0.15);
  border-radius: 2px;
}
.sutra-body::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 165, 116, 0.3);
}
</style>
