# Adam2027

短视频内容生产工具库。

## 爆款短视频脚本 Skill（5E 公式）

位置：`.claude/skills/short-video-script/`

把任意素材（一段经历、一次采访、一个想法）加工成可直接开拍的短视频脚本，
输出逐镜分镜、3 个备选钩子、日语口播与字幕、发布包装和自检打分。

**5E**：Engage 抓住 → Emotion 共鸣 → Education 价值 → Entertainment 有趣 → Encourage 行动

### 怎么用

在本仓库目录下开一个 Claude Code 会话，直接把素材丢进去即可，例如：

```
上周带日本朋友去了海底捞，她被免费美甲惊到了，做一条视频
```

skill 会自动触发，跑完整条生产线。

### 结构

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 主流程：算法映射、5 步生产线、输出格式、打分标准 |
| `references/hooks.md` | 10 类钩子模板 + 日语实例 + 平淡句改写对照 |
| `references/formats.md` | 5 种视频形态的逐秒节奏表 + 剪辑清单 |
| `references/topics.md` | 中日选题库、认知差清单、雷区 |
| `references/publish.md` | 标题、封面、标签、置顶评论、数据复盘 |
| `assets/script-template.md` | 交付模板 |
| `examples/friends.md` | 成品示例（日语面向日本人） |
| `examples/rules.md` | **已验证的成品**（中文口播 + 日本视角），逐句解剖 + 可复用模板 |
