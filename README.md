# Advisor Review Search Platform v1.3

导师评价搜索平台 — 多源聚合导师评价查询与智能分析系统。

---

## 功能

| 模块 | 说明 |
|------|------|
| **9 大搜索源** | GradChoice · PI Review · 导师评价网 · 保研论坛 · 小木虫 · 考研论坛 · LetPub NSFC · GitHub RMS · Tavily 广域搜索 |
| **导师画像** | DeepSeek 聚合提取导师形象：指导风格、人品师德、学术水平、学生出路、风险等级、关键词标签 |
| **六维雷达评分** | 6 路 DeepSeek 并行评分：学术水平、指导风格、人品师德、师生关系、科研经费、学生出路 |
| **Red Flag 检测** | 11 组正则模式自动标记：换导师、PUA、延毕、精神压榨等危险信号，本地+AI 双引擎 |
| **双引擎情感分析** | SnowNLP 本地引擎 + DeepSeek LLM 逐条情感分类，Tab 切换对比 |
| **KPI 监控仪表板** | 左侧可展开侧边栏：覆盖率、搜索延迟、DeepSeek 累计调用、爬虫成功率等实时仪表 |
| **导师详情页** | 集中展示全部评论 + DeepSeek AI 导师画像 + 多维度卡片 |
| **持久化全落盘** | 搜索历史、情感分析、DeepSeek 结果、六维评分、导师画像全部落盘 SQLite，重启不丢失 |
| **多源融合** | 自动按导师+院校合并多平台评价，URL 去重、来源加权排名 |
| **离线数据库** | 启动时自动从 Gitee/GitHub 镜像导入 RateMySupervisor 开源数据集（FTS5 全文索引） |
| **免责声明** | 完整的信息来源/学术用途/法律合规/责任限制声明页面 |

---

## 数据源

| 平台 | Tier | 状态 | 技术 |
|------|:----:|:----:|------|
| **GradChoice 研选** | 1 | ✅ | JWT Bearer + HTML/API 双解析 |
| **PI Review** | 1 | ✅ | `/search/?q=` SSR 搜索，评价全公开 |
| **导师评价网 dsPJ.net** | 1 | ✅ | 四级树状导航按需查找 |
| **保研论坛 eeban** | 5 | ✅ | Discuz! X3.4，版块 fid 限定搜索 |
| **小木虫 muchong** | 5 | ✅ | `wd` 参数搜索，降级校名兜底 |
| **考研论坛 kaoyan** | 5 | ✅ | POST + formhash + UTF-8，单关键词策略 |
| **GitHub RMS** | 4 | ✅ | 启动时自动导入（Gitee > GitHub > 镜像） |
| **Tavily 广域搜索** | 1 | ✅ | 按站点域精确搜索 |
| **LetPub NSFC基金** | 3 | ✅ | 纯 requests POST + PHPSESSID Cookie |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + TDesign UI + ECharts 5 |
| 后端 | Python 3.10+ + FastAPI + Uvicorn |
| 爬虫 | requests + BeautifulSoup4 + lxml |
| 浏览器自动化 | Playwright（LetPub 已退休，改用纯 requests） |
| 搜索引擎 | Tavily Search API |
| NLP | SnowNLP + jieba（本地）/ DeepSeek API（远程 6 路并行） |
| 存储 | SQLite（历史/分析/维度评分/画像/GitHub 数据）+ JSON（配置） |
| 数据集 | RateMySupervisor — FTS5 全文索引 |

---

## 快速开始

```bash
# 1. 安装后端依赖
cd backend && pip install -r requirements.txt

# 2. 安装前端依赖  
cd ../frontend && npm install

# 3. 一键启动（Windows）
cd .. && start.bat

# 或分别启动
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 配置步骤

### GradChoice 认证

1. 浏览器登录 [gradchoice.org](https://gradchoice.org)，F12 → Console 输入 `localStorage.getItem('access_token')`
2. Settings → GradChoice → 粘贴 Token → Verify

### LetPub NSFC 基金查询

3. 浏览器登录 [letpub.com.cn](https://www.letpub.com.cn/index.php?page=login)
4. F12 → Application → Cookies → 复制 `PHPSESSID` 的值
5. Settings → LetPub Authentication → 粘贴 PHPSESSID → Save → Verify

### DeepSeek AI（推荐）

6. 注册 [DeepSeek](https://platform.deepseek.com/) 获取 API Key
7. Settings → DeepSeek API → 粘贴 → 画像 + 六维评分 + 情感分类全部可用

### Tavily 搜索（推荐）

8. 注册 [Tavily](https://tavily.com) 获取免费 Key
9. Settings → Tavily → 粘贴 → Check Connectivity

### GitHub 离线数据库（自动）

10. 启动时自动从 Gitee 镜像导入数据集，无需手动操作

---

## 页面导航

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Home | 首页搜索入口 |
| `/search` | Search | 搜索结果 + Detail 入口 |
| `/analysis` | Analysis | 三引擎分析（情感/DeepSeek/六维） |
| `/advisor` | Advisor Detail | 全部评论 + AI 导师画像 |
| `/history` | History | 搜索历史 + 详情弹窗 |
| `/settings` | Settings | 配置管理（API Key / Cookie / 平台开关） |
| `/disclaimer` | Disclaimer | 免责声明 |

---

## 项目结构

```
├── backend/
│   └── app/
│       ├── main.py              # 入口 + lifespan 启动事件
│       ├── config.py            # 多平台配置
│       ├── db.py                # SQLite 持久化
│       ├── models.py            # Pydantic 模型
│       ├── routers/
│       │   ├── search.py        # 搜索调度（9 源并行）
│       │   ├── analysis.py      # 六维评分 + 情感 + DeepSeek + 画像
│       │   ├── settings.py      # 配置管理 + 验证端点
│       │   ├── history.py       # 搜索历史 CRUD
│       │   └── stats.py         # KPI 统计 API
│       ├── services/
│       │   ├── scorer.py        # 六维雷达评分引擎
│       │   ├── search_engine.py # Tavily 搜索引擎
│       │   ├── merger.py        # 多源融合去重排名
│       │   ├── nlp_engine.py    # NLP + Red Flag + DeepSeek + 画像
│       │   ├── github_import.py # GitHub 数据集导入
│       │   └── crawlers/
│       │       ├── gradchoice.py      # GradChoice 爬虫
│       │       ├── pireview.py        # PI Review 爬虫
│       │       ├── daoshipingjia.py   # dsPJ.net 爬虫
│       │       ├── eeban.py           # 保研论坛爬虫
│       │       ├── muchong.py         # 小木虫爬虫
│       │       ├── kaoyan.py          # 考研论坛爬虫
│       │       └── letpub.py          # LetPub NSFC 基金
│       └── utils/
│           ├── rate_limiter.py
│           └── proxy_manager.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── HomePage.tsx
│       │   ├── SearchPage.tsx
│       │   ├── AnalysisPage.tsx       # 三引擎分析
│       │   ├── AdvisorDetailPage.tsx  # 导师详情 + 画像
│       │   ├── HistoryPage.tsx
│       │   ├── SettingsPage.tsx
│       │   └── DisclaimerPage.tsx     # 免责声明
│       ├── components/
│       │   ├── RadarChart.tsx         # 六维雷达图
│       │   ├── SentimentChart.tsx     # 情感柱状图（紧凑模式）
│       │   ├── KpiSidebar.tsx         # KPI 监控仪表板
│       │   ├── PlatformSelector.tsx
│       │   ├── ResultCards.tsx        # 可展开评论 + Detail 按钮
│       │   ├── SearchForm.tsx
│       │   └── CoolSlogan.tsx
│       └── services/
│           └── api.ts
├── tests/                         # 测试脚本
├── data/                          # 运行时数据
├── start.bat                      # 一键启动
├── 导师评价搜索平台可行性研究报告.md
├── 二档调研报告.md
└── daoshipingjia调研报告.md
```

---

## v1.3 更新日志

### 新增数据源（1 个）

- **考研论坛 bbs.kaoyan.com** — POST + formhash + UTF-8 搜索，单关键词策略，正文全公开

### LetPub 重大升级

- 从 Playwright Sync → Async → SelectorEventLoop → Multiprocessing → 最终发现纯 `requests` POST 到 `nsfcfund_search.php` 即可
- 仅需 PHPSESSID Cookie，设置页引导用户手动粘贴
- 批准年份范围自动设为 1997-2023，覆盖全部历史项目

### 新增前端页面（3 个）

- **导师详情页 `/advisor`** — 集中展示全部评论 + DeepSeek 聚合生成导师画像（指导风格/人品师德/学术水平/学生出路/风险等级/关键词/推荐意见）。画像落盘持久化，重启不丢失。
- **KPI 监控仪表板** — 左侧可展开/收起侧边栏，四组指标：数据覆盖（GitHub 导师数/唯一导师/评论数）、搜索性能（总搜索次数/平均延迟/Tavily 状态）、AI 分析（SnowNLP/DeepSeek/维度评分调用数）、数据源（平台列表+使用频率条形图）。每 30 秒自动刷新。
- **免责声明页 `/disclaimer`** — 7 章节：信息来源、用户内容、删除/更正请求、学术用途、法律合规、禁止行为、责任限制。

### 分析引擎升级

- **DeepSeek 逐条情感分类** — SnowNLP 区域新增"Re-analyze with DeepSeek"按钮，LLM 逐条判断正/负/中性，Tab 页切换对比 SnowNLP 本地结果与 DeepSeek LLM 结果
- **导师画像引擎** — DeepSeek 聚合全部评论提取六大维度画像
- **全面落盘** — SnowNLP 结果、DeepSeek 情感分类、DeepSeek 综合分析、六维评分、导师画像全部持久化到 SQLite，页面加载自动恢复，不再每次重新计算

### 体验优化

- 搜索结果评论可展开全部 / 收起，不再截断
- 分析页底部新增整排 Advisor Detail 按钮，一键跳转详情页
- 历史页 Tag 显示实际评论数（非融合条目数），弹窗新增好评率统计
- Tavily API Key 预览持久化
- 分析页评论分隔符从 `\n` 改为 `\n\n`，修复 SnowNLP 把全部评论当一条的问题

### 基础设施

- 数据源从 8 个扩展到 9 个（考研论坛）
- LetPub 启用默认配置
- 前端路由从 5 个扩展到 8 个
- 新增 `stats` 路由模块 + `advisor_profile_json` 数据库列自动迁移

---

## v1.2 更新日志

- 新增 PI Review、dsPJ.net、保研论坛、小木虫 4 个数据源
- 六维雷达评分 + Red Flag 自动检测
- 降级搜索策略 + GitHub 镜像链路
- 数据源翻倍：4 → 8

---

## v1.1 更新日志

- Tavily Search API 多源搜索
- GitHub 数据集预加载 + FTS5 全文索引
- 多源融合引擎 + 设置页重构
- SQLite 持久化 + Token Bucket 限速器

---

## 已知限制

- **Tavily**：依赖 API Key，免费额度 1000 次/月
- **dsPJ.net**：低分导师(≤3.8)姓名隐藏，评价原文需会员
- **LetPub**：仅覆盖自然科学基金项目，不包含社科基金
- **ratemyprofessor.online**：541 所中国大学，需 Playwright 渲染（后续版本）

---

## 爬虫小故事

开发过程中遇到了不少有趣的技术问题，记录如下，以飨后来者。

### LetPub 的四小时 debug 长征

LetPub 是国自然基金查询网站，数据由 layui 框架动态加载，初版使用 Playwright 模拟浏览器操作。看起来很简单：打开页面 → 填表单 → 点搜索 → 解析表格。但实际运行时报 `NotImplementedError: create_subprocess_exec`。

**第一回合**：`sync_playwright` 在 FastAPI 的 `asyncio.to_thread()` 子线程中调用，Windows 的 `ProactorEventLoop` 不支持子进程。尝试在线程中创建新的事件循环 —— 失败。

**第二回合**：改用 `async_playwright`，在主事件循环中直接 `await`。uvicorn `--reload` 模式下主事件循环仍然是 Proactor 的，报同样的错误。

**第三回合**：在 `main.py` 顶部强制切换到 `WindowsSelectorEventLoopPolicy`。但 uvicorn `--reload` 的子进程在 import 之前就已经固定了事件循环策略，修改无效。

**第四回合**：在 LetPub 模块内手动创建 `SelectorEventLoop` + 独立线程来跑 Playwright。Python 3.10 在 Windows 上的 SelectorEventLoop 的 `_make_subprocess_transport` 竟然是 `raise NotImplementedError` —— 两个事件循环在 Windows 上都废了。

**第五回合**：上 `multiprocessing.Process`，spawn 模式启动全新 Python 进程。依然报 NotImplementedError。Python 3.10.8 的 Windows 实现在子进程管理上有根本性的缺陷。

**绝杀**：打开浏览器 F12，看网络面板。`checksubmit` 函数触发了 POST 到 `nsfcfund_search.php?mode=advanced&datakind=list&currentpage=1`，参数就是表单字段 + `searchsubmit=true`。直接用 `requests.post()` 试了一下 —— 21,829 字节的 HTML 表格回来了，5 条基金数据整整齐齐。根本不需要浏览器。

从 Playwright 四层架构（sync→async→thread→multiprocess）退化到纯 requests 一行 POST，debug 耗时 4 小时，最终方案耗时 0.3 秒。教训：先看网络面板，别急着上浏览器自动化。

### 考研论坛的编码暗战

考研论坛 bbs.kaoyan.com 是一个 Discuz! X3.2 论坛。第一个测试脚本用 GBK 编码搜索"导师"——返回 0 条结果。换用搜索表单的 POST 端点，`srchtxt=导师`，还是 0。一度怀疑是不是登录墙。

翻阅页面源码发现 `<meta charset="utf-8">`，把请求编码从 GBK 切换为 UTF-8 —— 瞬间 500 条结果。DZ X3.2 对不同页面用了不同编码：列表页 GBK、搜索 API UTF-8。

随后又踩了第二个坑：爬虫用"选导师"三个字搜索（空格分隔多关键词），返回 0。用"选 导师"搜索，依旧是 0。最终发现考研论坛的搜索是 AND 精确匹配 —— "选 导师"要求标题同时包含"选"和"导师"两个词，而实际标题是"选导师经验分享"。改用单核心词"导师"搜索后，返回 500 条，在本地用 Python 做标题/内容二次过滤，命中率大幅提升。

### 评论被当成一整条的幽灵 bug

SnowNLP 情感分析引擎分两步工作：前端把多条评论用分隔符拼成一个大字符串 → 后端用 `\n{2,}`（至少两个连续换行）把字符串拆回多条评论、逐条打分。但前端用的拼接符是 `\n`（单个换行），导致 87 条评论被当作一整段文本。SnowNLP 永远只返回一个整体得分，前端永远显示"积极：1，中性：0，负面：0"。

修起来很简单 —— 把 `join('\n')` 改成 `join('\n\n')`。但症状太迷惑：87 条评论，1 个积分，87 这个数字哪里都不显示。用户在分析页看到的是"87 reviews analyzed"，但 SnowNLP 只处理了一条，其余 86 条被吞了。前后端只差一个换行符。

### 表格里藏了 21KB 的 AJAX 响应

LetPub 搜索后的页面，浏览器的 Elements 面板显示表格 `<tbody>` 里确实有 `<td>` 数据。Playwright 的 `wait_for_function` 等 `tbody tr td` 等到超时。因为表格是空的 `<tbody>` —— layui 框架把 AJAX 返回的 HTML 片段渲染到了另一个容器里，再动态更新到 `keyword-datalist` 表格中。Playwright 等的是页面渲染后的 DOM，但 layui 的渲染时机和 Playwright 的等待函数之间存在竞态。

最后不需要等待：直接用 `requests` POST 拿到 AJAX 端点的原始 HTML，BeautifulSoup 解析，5 条记录整整齐齐。从"等不到数据"到"数据本来就在那里"，中间隔了一个 AJAX 的异步渲染层。
