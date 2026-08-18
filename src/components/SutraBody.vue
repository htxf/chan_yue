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
    
    <!-- 底部留白，避免被播放条遮挡 -->
    <div class="bottom-spacer"></div>
  </div>
</template>

<style scoped>
.sutra-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 40px;
  max-width: 680px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.bottom-spacer {
  height: 120px;
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
