# ai-journey

我的 AI 学习轨迹 —— 笔记、每周练习、作品集。

**主线：大模型应用开发 → Agent 工程。**
目标：90 天后交付 1 个可公网访问的旗舰项目 + 完整作品集。

---

## 进度

| 阶段 | 周次 | 主题 | 产出 | 状态 |
|---|---|---|---|---|
| 一、环境与第一口氧气 | W01 | 环境搭建、跑通第一个 Agent | 本地模型对话 + Colab Agent | ⬜ |
| 二、Python 工程能力 | W02–W03 | Python 进阶 / FastAPI / Git | 可 HTTP 调用的 AI 问答接口 | ⬜ |
| 三、API 与 Prompt 工程 | W04 | 模型 API、Prompt 工程 | 3 个 LLM 应用 + Prompt 模板库 | ⬜ |
| 四、RAG 入门 | W05–W06 | 切片 / Embedding / 向量库 | 知识库助手 v1 | ⬜ |
| 五、RAG 进阶 | W07–W08 | 混合检索 / Rerank / 评估 | **生产级 RAG 系统（含引用+评估）** | ⬜ |
| 六、Agent 工程 | W09–W10 | Function Calling / ReAct / LangGraph / MCP | **多步任务 Agent（含人工确认）** | ⬜ |
| 七、生产化与包装 | W11–W12 | Docker / 部署 / 可观测性 / 成本 | 部署上线 + 作品集 + 简历 | ⬜ |

> 状态标记：⬜ 未开始 / 🟨 进行中 / ✅ 完成

---

## 目录

```
ai-journey/
├── README.md        # 你在这里：目标与进度
├── notes/           # 学习笔记，按周 w01.md、w02.md ...
├── weekly/          # 每周练习代码 w01/ w02/ ...
├── projects/        # 作品集，一个项目一个子目录
├── playground/      # 随手试验、临时脚本
└── templates/       # 笔记与项目案例模板
```

---

## 作品集项目清单

- [ ] `projects/rag-kb/` —— 生产级 RAG 知识库助手（旗舰项目）
- [ ] `projects/agent-demo/` —— 多步任务 Agent
- [ ] `projects/eval-dashboard/` —— 多模型评估看板
- [ ] `projects/vertical-ai/` —— 垂直行业 AI 应用

每个项目用 `templates/project-case-study.md` 的结构写成**工程案例**，而不只是上传源码。

---

## 快速开始

```powershell
# 环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # 后续按需要添加

# 密钥：复制模板后填入自己的 key，.env 不会被提交
Copy-Item .env.example .env
```

---

## 接入 GitHub（首次只需一次）

本仓库已经初始化好（分支 `main`），只差登录 GitHub 并推送：

```powershell
gh auth login                       # 浏览器授权，只需一次
powershell -ExecutionPolicy Bypass -File .\setup-remote.ps1
```

第二条命令会自动完成：配置 git 身份 → 首次提交 → 创建 GitHub 仓库 → 关联并推送。
也可以直接双击 `setup.bat` 完成同样的事。

推送成功后，日常只需要三步：

```powershell
git add -A
git commit -m "docs: w02 笔记"
git push
```

---

## 学习原则

1. **不要贪多** —— 选一条路线学完，胜过东学一点西学一点
2. **第 4 周必须开始写项目** —— 不要等课程全部看完
3. **先跑通再理解** —— 让代码先跑起来，原理后面自然懂
4. **每学一个模块立刻用在项目里**
5. **密钥永不进仓库** —— 全部走 `.env`
