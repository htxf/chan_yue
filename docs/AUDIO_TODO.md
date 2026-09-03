# 《金刚经》母带音频待重跑与字音校正追踪档案 (AUDIO_TODO)

本文档永久记录双音色母带生成管线中已解决、待生成及配额管理的全部细节，供配额刷新后直接无缝恢复执行。

---

## 一、配额限制与运行策略

- **Gemini TTS Preview (gemini-3.1-flash-tts)** 当前处于免费层（Free Tier）。
- **配额上限**：每日限额为 **10 次请求 / 天 / 模型**（GenerateRequestsPerDayPerProjectPerModel-FreeTier）。
- **生成开销**：每一品生成双音色（Zephyr 女声 + Charon 男声）需消耗 **2 次调用**。每日最多可完整构建 **5 个章节**。
- **重跑恢复方式**：配额自动重置后，按章节执行脚本即可。

---

## 二、各章节音频现状与待解决清单

| 章节 | 当前状态 | 待解决问题要点 | 预定执行命令 |
| :--- | :--- | :--- | :--- |
| **第 4 品** | 已完成 | 开篇品题朗诵（0.12s~2.56s）+ 否也，世尊修复 + DP 时间轴校准 100% 就绪 | 已落地，无需重跑 |
| **第 5 品** | 待重跑（优先级 1） | 1. 补开篇品题朗读：“如理实见分第五。”<br>2. 修复须菩提回答“不也，世尊”读为“否也，世尊（fou ye）” | python scripts/generate_chapter_master.py jingangjing chapter_5 |
| **第 7 品** | 待重跑（优先级 2） | 1. 补开篇品题朗读：“无得无说分第七。”<br>2. 落实“阿耨多罗”强制映射为“阿诺多罗”（确保 N 音 nuo，杜绝旧版的 L 音漏）<br>3. 消除问句尾部“耶？”急促上扬抢速（已在脚本替换为平稳“耶。”），女声/男声调校至统一基准 | python scripts/generate_chapter_master.py jingangjing chapter_7 |
| **第 1 品** | 待重跑 | 补开篇品题朗读：“法会因由分第一。”（当前正文与时间轴正常） | python scripts/generate_chapter_master.py jingangjing chapter_1 |
| **第 2 品** | 待重跑 | 补开篇品题朗读：“善现启请分第二。”（当前正文与时间轴正常） | python scripts/generate_chapter_master.py jingangjing chapter_2 |
| **第 3 品** | 待重跑 | 补开篇品题朗读：“大乘正宗分第三。”，微调女声基频保持空灵一致 | python scripts/generate_chapter_master.py jingangjing chapter_3 |
| **第 6 品** | 待重跑 | 补开篇品题朗读：“正信希有分第六。”（正文 21 发声段已校准，仅需补题） | python scripts/generate_chapter_master.py jingangjing chapter_6 |
| **第 8 品** | 待重跑 | 补开篇品题朗读：“依法出生分第八。”（当前正文与时间轴正常） | python scripts/generate_chapter_master.py jingangjing chapter_8 |

---

## 三、流水线字音强制替换规范（已在脚本内锁定）

- 阿耨多罗 -> 阿诺多罗（锁定鼻辅音 N：nuo，杜绝混淆成 lou）
- 三藐 -> 三秒（san miao）
- 耶？/ 耶? -> 耶。（消除疑问尾音上扬变调，保持平稳持诵）
- 不也 -> 否也（fou ye 佛经古音正读）
- 四句偈 -> 四句记（ji 四声）
- 其福胜彼 -> 其福圣彼（sheng 四声）
- 为他人说 -> 位他人说（wei 四声）
- 可思量不 / 见如来不 / 生实信不 / 宁为多不 -> ...否（fou）
- 著衣持钵 / 着衣持钵 / 右膝着地 / 著我人 -> 浊...（zhuo 二声）
- 应云何 / 应如是 / 应无所住 / 不应取 / 法尚应舍 -> 英...（ying 一声）
- 我相 / 人相 / 众生相 / 寿者相 / 法相 / 非法相 -> ...向（xiang 四声）

