# AI-Daily-Briefing — AI 行业日报

## 项目目的

每天自动收集和整理 AI 行业最新动态，覆盖三个维度：
- **科研学术**：重要论文、基准突破、新架构/方法
- **产品应用**：新产品发布、重大功能更新、企业级应用
- **融资进展**：融资轮次、金额、投资方、估值变化

每项覆盖国内和国际两个视角。

## 公开访问

🌐 **https://leoljq.github.io/AI-Daily-Briefing/**

任何设备浏览器打开即可查看。自包含网页，不依赖服务器。

## 目录结构

```
AI-Daily-Briefing/
├── CLAUDE.md              ← 本文件
├── index.html             ← 自包含网页（build_site.py 生成）
├── build_site.py          ← Markdown → HTML 构建脚本
├── view.bat               ← 本地双击打开
├── prompt-template.md     ← 日报生成 prompt 模板
├── .gitignore
└── daily-briefings/       ← 日报存档
    └── YYYY-MM-DD.md      ← 按日期命名
```

## 自动化流水线

```
每天早上 8:07（CronCreate 触发）
  ├── 1. WebSearch × 6（科研/产品/融资 × 国际/国内）
  ├── 2. 生成 daily-briefings/YYYY-MM-DD.md
  ├── 3. python build_site.py → 重建 index.html
  └── 4. git add → commit → push → GitHub Pages 自动更新
```

## 运行方式

- **自动**：CronCreate 每天晚上 9:07 触发完整流水线
- **手动**：说"生成今天的 AI 日报"
- **本地查看**：双击 `view.bat` 或在浏览器打开 `index.html`
- **远程查看**：https://leoljq.github.io/AI-Daily-Briefing/

## 日报规范

- 每条消息 2-3 句话，附来源链接
- 「今日重点」选 2-3 条最重要的，各写一段简短分析
- 语言：中文
- **硬性日期标准**：只收录当天或昨天的内容。每条文章必须能从搜索结果中确认发布日期。无法确认日期的直接跳过，宁缺毋滥。不要用旧文凑数。
- 来源多样性：每条至少覆盖 2 个不同来源

## 质量检查

生成后自检：
- [ ] 三个维度都有内容
- [ ] 国内和国际都有覆盖
- [ ] 每条有来源链接
- [ ] 今日重点有分析，不只是复述
- [ ] 没有幻觉链接（链接能点开）

## 禁止

- 不要编造链接或论文标题
- 不要把旧闻当新闻（超过 48 小时的标注为「补遗」）
- 不要跳过任何一个维度

## 部署

- GitHub: git@github.com:LeoLJQ/AI-Daily-Briefing.git
- 分支: main
- Pages: 从 main 分支根目录部署
- 推送后约 30 秒自动生效
