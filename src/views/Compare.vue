<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

// 焦点测试数据
const sections = [
  {
    id: 'diyi',
    title: '焦点 1：男声“法会因由分第一”',
    desc: '原理：输入“法会因由分第一品”，让模型把“第一”作为重音中气读满，在 1655ms 处毫秒级裁切“品”。实测尾字能量由 -34.5 dBFS 暴增至 -29.7 dBFS，峰值飙升 +6.9 dB！',
    tagColor: 'amber',
    cases: [
      {
        name: '1. 原版（末尾句号，严重偷气变轻声虚脱）',
        tag: '原版 · 能量 -34.5 dBFS',
        tagType: 'danger',
        quote: '法会因由分<span class="err">第一</span>。（有气无力，尾音下坠）',
        src: '/audio/compare/v3_diyi_orig.mp3'
      },
      {
        name: '2. 方案一：垫字切除（法会因由分第一[品]）',
        tag: '推荐 · 峰值暴增 +6.9 dB',
        tagType: 'success',
        quote: '法会因由分<span class="hl">第一</span>。（重音挺立，掷地有声，消除偷气）',
        src: '/audio/compare/v3_diyi_trimmed.mp3'
      }
    ]
  },
  {
    id: 'ch2_title',
    title: '焦点 2：男声“善现启请分第二”',
    desc: '原理：输入“善现启请分第二品”，在 1544ms 处毫秒级裁切“品”，品序结句刚健饱满，峰值提升 +3.8 dB。',
    tagColor: 'blue',
    cases: [
      {
        name: '1. 原版（善现启请分第二。）',
        tag: '原版 · 句末下坠',
        tagType: 'danger',
        quote: '善现启请分<span class="err">第二</span>。（末尾“二”字能量衰减）',
        src: '/audio/compare/v3_ch2_title_orig.mp3'
      },
      {
        name: '2. 方案一：垫字切除（善现启请分第二[品]）',
        tag: '方案一 · 饱满干脆',
        tagType: 'success',
        quote: '善现启请分<span class="hl">第二</span>。（品序干脆挺拔，无下坠虚脱）',
        src: '/audio/compare/v3_ch2_title_trimmed.mp3'
      }
    ]
  },
  {
    id: 'pusa',
    title: '焦点 3：女声“诸菩萨”尾音对比',
    desc: '对比三种状态：① 原版句末四声（受先验拖累拉长成拖沓 saaaa）；② 方案一：垫字“众”连读后裁切（让“萨”作为过渡音节发实声四声，零气声拖音）；③ 显式轻声（pu 2 sa 5）。',
    tagColor: 'rose',
    cases: [
      {
        name: '1. 原版四声（句末标点前，元音被拉长拖沓）',
        tag: '原版 · 尾音拖沓 saaaa',
        tagType: 'danger',
        quote: '如来善护念诸<span class="err">菩萨</span>，善付嘱诸<span class="err">菩萨</span>。',
        src: '/audio/compare/v3_pusa_orig.mp3'
      },
      {
        name: '2. 方案一：垫字“众”连读后裁切（诸菩萨[众]）',
        tag: '方案一 · 实声利落',
        tagType: 'success',
        quote: '如来善护念诸<span class="hl">菩萨</span>，善付嘱诸<span class="hl">菩萨</span>。（四声实声收尾，消除气声拖音）',
        src: '/audio/compare/v3_pusa_trimmed.mp3'
      },
      {
        name: '3. 你的提议：显式轻声版（pu 2 sa 5）',
        tag: '显式轻声 · 横向盲测',
        tagType: 'info',
        quote: '如来善护念诸<span class="hl">菩萨(轻声)</span>，善付嘱诸<span class="hl">菩萨(轻声)</span>。',
        src: '/audio/compare/v3_pusa_neutral.mp3'
      }
    ]
  },
  {
    id: 'shanzai',
    title: '焦点 4：女声“善哉！善哉！”连贯度',
    desc: '对比：原版呼赞叹词中间隔 380ms 且带叹号，首个“哉”严重拖长；方案一按四字连词“善哉善哉[矣]”合成并切除“矣”，节奏紧凑顿挫。',
    tagColor: 'emerald',
    cases: [
      {
        name: '1. 原版（善哉！善哉！）',
        tag: '原版 · 2.3秒散漫拖长',
        tagType: 'danger',
        quote: '善哉！善哉！（中间断裂冷场，首个“哉”严重拖音）',
        src: '/audio/compare/v3_shanzai_orig.mp3'
      },
      {
        name: '2. 方案一：四字成词连诵 + 垫字切除（善哉善哉[矣]）',
        tag: '方案一 · 1.0秒顿挫分明',
        tagType: 'success',
        quote: '善哉善哉。（紧凑顿挫，一气呵成，行云流水）',
        src: '/audio/compare/v3_shanzai_trimmed.mp3'
      }
    ]
  }
]
</script>

<template>
  <div class="min-h-screen w-full bg-[#0a0a0f] text-[#f2ece2] px-4 py-6 pb-20 font-serif selection:bg-[#d4a574]/20">
    <div class="max-w-[640px] mx-auto">
      <!-- 顶栏导航 -->
      <header class="flex items-center justify-between pb-4 border-b border-white/10 mb-6">
        <button
          @click="goBack"
          class="flex items-center gap-1.5 text-xs text-white/70 hover:text-[#d4a574] transition-colors py-1.5 px-3 rounded-full bg-white/5 active:scale-95 cursor-pointer"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          <span>返回</span>
        </button>
        <div class="text-center">
          <h1 class="text-base font-bold text-[#d4a574] tracking-wide flex items-center gap-1.5 justify-center">
            <span>⚡</span> 声学母带实验室
          </h1>
          <p class="text-[11px] text-white/50 mt-0.5">方案一：声学垫字切除实测</p>
        </div>
        <div class="w-14"></div>
      </header>

      <!-- 导言说明 -->
      <div class="bg-white/5 border border-white/10 rounded-2xl p-4 mb-6 text-xs text-white/70 leading-relaxed">
        <div class="font-bold text-white/90 mb-1 flex items-center gap-1.5">
          <span class="text-[#d4a574]">💡</span> 第一性原理验证
        </div>
        <p>
          解决大模型在句末因“句号/逗号”触发能量下倾与虚脱轻声的问题。通过在短语后垫字连读使重音挺立，再毫秒级精准裁切垫字，对比原版与切除版听感。
        </p>
      </div>

      <!-- 四大焦点对比卡片 -->
      <div class="space-y-6">
        <section
          v-for="sec in sections"
          :key="sec.id"
          class="bg-[#121218] border border-white/10 rounded-2xl p-4 shadow-lg"
        >
          <h2 class="text-sm font-bold text-white/90 flex items-center gap-2 mb-1.5">
            <span class="text-amber-400">●</span>
            <span>{{ sec.title }}</span>
          </h2>
          <p class="text-[12px] text-white/60 leading-relaxed mb-4">
            {{ sec.desc }}
          </p>

          <div class="space-y-3">
            <div
              v-for="(c, ci) in sec.cases"
              :key="ci"
              class="rounded-xl p-3.5 border transition-all"
              :class="{
                'bg-rose-950/10 border-rose-500/25': c.tagType === 'danger',
                'bg-emerald-950/15 border-emerald-500/30': c.tagType === 'success',
                'bg-sky-950/15 border-sky-500/25': c.tagType === 'info'
              }"
            >
              <div class="flex items-center justify-between gap-2 mb-2">
                <span
                  class="text-xs font-semibold"
                  :class="{
                    'text-rose-300': c.tagType === 'danger',
                    'text-emerald-300': c.tagType === 'success',
                    'text-sky-300': c.tagType === 'info'
                  }"
                >
                  {{ c.name }}
                </span>
                <span
                  class="text-[10px] px-2 py-0.5 rounded-full shrink-0 font-medium"
                  :class="{
                    'bg-rose-500/20 text-rose-300': c.tagType === 'danger',
                    'bg-emerald-500/20 text-emerald-300': c.tagType === 'success',
                    'bg-sky-500/20 text-sky-300': c.tagType === 'info'
                  }"
                >
                  {{ c.tag }}
                </span>
              </div>

              <div
                class="text-xs text-white/80 bg-black/30 px-3 py-2 rounded-lg mb-2.5 leading-relaxed [&_.hl]:text-amber-400 [&_.hl]:font-bold [&_.hl]:underline [&_.err]:text-rose-400 [&_.err]:line-through"
                v-html="c.quote"
              ></div>

              <!-- 原生高保真音频播放器 -->
              <audio
                controls
                preload="metadata"
                :src="c.src"
                class="w-full h-9 rounded-lg"
              ></audio>
            </div>
          </div>
        </section>
      </div>

      <!-- 底部提示 -->
      <div class="mt-8 text-center text-[11px] text-white/40">
        禅阅实验室 · 毫秒级物理波形切除直出
      </div>
    </div>
  </div>
</template>

<style scoped>
audio {
  accent-color: #d4a574;
}
audio::-webkit-media-controls-panel {
  background-color: rgba(255, 255, 255, 0.08);
}
</style>
