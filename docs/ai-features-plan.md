# Plane 自托管 AI 能力实现计划

> 文档版本：v0.1
> 日期：2026-09-18
> 适用范围：基于 Plane Community Edition（AGPL-3.0）自托管实例
> 目标仓库：`aidai524/team`

---

## 1. 背景与目标

### 1.1 背景

我们已基于 Plane **社区版（Community Edition）** 自托管了一套团队协作系统：

- 实例地址：`https://team.stableflow.ai`
- 版本：`v1.4.2`（官方发布镜像，Docker Compose 部署）
- 部署目录：`/root/plane-selfhost/`（`setup.sh` + `plane-app/`）
- 邮件：Resend SMTP（发件域 `mailserver.stableflow.ai`）

Plane 官方内置的 AI 能力 **Plane AI（Pi）** 属于 **商业版（Pro / Business / Enterprise）**，闭源，且自托管启用 AI 还需要额外部署 `PI` 微服务 + OpenSearch + 独立数据库，成本与资源要求都很高。

### 1.2 目标

在**不依赖商业版**的前提下，基于社区版自建一套可迭代的 AI 能力，分阶段交付：

1. 让团队能用自然语言**查询**工作区数据（只读问答）。
2. 让 AI 能**安全地创建/修改**工作项等实体（计划 → 确认 → 执行）。
3. 让 AI **深入页面编辑器**（改写、扩写、生成内容块）。
4. 提供 **AI Skills（自定义斜杠命令）** 与 **外部工具接入（MCP）**。
5. 具备**用量统计、权限控制**与可运维性。

### 1.3 非目标（本阶段不做）

- 不追求一次性完整对标商业版 Plane AI（工程量过大）。
- 不引入 OpenSearch（当前服务器资源不足），检索统一用 Postgres + pgvector。
- 不 fork / 修改 Plane 核心业务逻辑（保持可升级）。

---

## 2. 现状盘点

### 2.1 社区版已有的 AI「底子」（可复用）

| 已有能力 | 位置 |
| --- | --- |
| 单轮 LLM 调用接口 `/api/workspaces/{slug}/ai-assistant/` | `apps/api/plane/app/views/external/base.py` |
| 项目级调用接口 `/api/workspaces/{slug}/projects/{project_id}/ai-assistant/` | 同上 + `apps/api/plane/app/urls/external.py` |
| LLM 配置链路 `LLM_API_KEY` / `LLM_MODEL` / `LLM_PROVIDER` | `base.py`、`utils/instance_config_variables/core.py` |
| Provider 抽象（OpenAI / Anthropic / Gemini，模型列表写死） | `base.py` 的 `SUPPORTED_PROVIDERS` |
| OpenAI SDK（`openai==1.63.2`，支持 `OPENAI_BASE_URL` 环境变量） | `apps/api/requirements/base.txt` |
| God Mode AI 配置页（模型名 + API Key） | `apps/admin/app/(all)/(dashboard)/ai/form.tsx` |
| 前端 `AIService`（`createGptTask` / `performEditorTask`） | `apps/web/core/services/ai.service.ts`（**死代码，无引用**） |
| i18n 文案与常量（`AI_EDITOR_TASKS`、`pi_chat` 等） | `packages/constants/src/ai.ts`、`packages/i18n/...` |

### 2.2 缺口（需自建）

| 缺失项 | 现状 |
| --- | --- |
| 前端聊天 UI（面板 / 全屏 / 历史会话 / 建议 / Thinking 面板） | 无 |
| 工具调用 / Agent 编排（function calling、动作卡片、确认流） | 无（只有单轮补全） |
| 检索层（向量 / 语义搜索） | 无（无 OpenSearch、无 pgvector、无 embedding） |
| 页面编辑器 AI（流式写入、逐块 proposal、选区改写、AI block） | 无（`rephrase-grammar` 后端不存在） |
| AI Skills（自定义斜杠命令 + 变量） | 无 |
| MCP 连接器（GitHub / Sentry / Granola 等） | 无 |
| 图表 / 周期分析 / 用量额度 / 权限 | 无 |

> 结论：社区版提供的是「**单轮 LLM 调用的骨架**」，其余几乎全部需要自建。

### 2.3 基础设施现状

| 项 | 现状 |
| --- | --- |
| 服务器 | 2 vCPU / 3.8 GB RAM / 78 GB 磁盘（Alpine Linux） |
| 部署方式 | Docker Compose（13 个容器） |
| 现有内存占用 | Plane 全套约 1.2 GB |
| 可用余量 | 约 1.8 GB（不足以运行 OpenSearch） |
| 数据库 | Postgres 15.7（容器内） |
| 缓存 | Valkey 7.2 |
| 对象存储 | MinIO |
| 队列 | RabbitMQ |

---

## 3. 约束

### 3.1 法律与许可（AGPL-3.0）

- 社区版代码为 **AGPL-3.0**，允许修改与扩展，包括自建 AI 功能。
- **内部自用**（不对第三方提供网络服务）：改动可私有，无开源义务。
- **对外提供网络服务**（SaaS / 给第三方使用）：必须向用户提供修改后的**完整源码**（AGPL §13）。
- **分发**镜像/二进制：必须附带源码。
- 不得复制商业版代码（闭源，且官方声明社区版与商业版无代码依赖）。
- 不得使用官方商标（"Plane AI"、"Pi"）误导性命名，本项目自命名。

> **架构层面的合规策略**：AI 以**独立服务**形式实现，通过 Plane 公开的 REST API / MCP 交互，避免形成对 AGPL 核心的深度衍生，降低合规与升级风险。

### 3.2 基础设施约束

- 当前服务器无法承载 OpenSearch（单实例通常需 ≥ 2 GB）。
- 所有新增组件必须控制在内存预算内（建议新增 ≤ 1 GB，必要时升配到 4 vCPU / 8 GB）。

### 3.3 LLM 选型

- 主选 **DeepSeek**（OpenAI 兼容）：
  - Base URL：`https://api.deepseek.com`
  - 模型：`deepseek-chat`（V3）、`deepseek-reasoner`（R1）
- 预留 OpenAI / Anthropic 作为可切换 provider。
- 注意：社区版 `OpenAIProvider.models` 为**写死白名单**，DeepSeek 模型名会被拒；需通过自定义 provider 或白名单扩展解决。

---

## 4. 架构设计

### 4.1 核心决策：独立 AI 服务（不深 fork 核心）

```
┌───────────────────────────────────────────────────────┐
│  Plane Web (React Router + MobX)                       │
│    └─ 新增 AI 面板 / 页面编辑器 AI 入口                  │
└──────────────────────────┬────────────────────────────┘
                           │ HTTPS（同域反代，如 /ai）
┌──────────────────────────▼────────────────────────────┐
│  AI Gateway (FastAPI)                                  │
│    ├─ Chat API（SSE 流式）                              │
│    ├─ Agent Orchestrator（tool calling）                │
│    ├─ LLM Adapter（DeepSeek / OpenAI / Anthropic）      │
│    ├─ Tool Layer → Plane REST API                       │
│    ├─ Retrieval（pgvector RAG）                         │
│    └─ Permission / Usage                                │
└───────┬───────────────────────┬───────────────────────┘
        │                       │
┌───────▼──────────┐   ┌────────▼───────────────────────┐
│ Postgres+pgvector│   │ Plane REST API (X-API-Key)      │
│ （AI 专用库）     │   │ /api/v1/...                     │
└──────────────────┘   └────────────────────────────────┘
```

### 4.2 为什么独立服务

1. **升级安全**：Plane 升级只需换镜像，AI 服务不受影响。
2. **合规清晰**：AI 服务为独立程序，通过公开 API 交互，降低 AGPL 衍生争议。
3. **迭代快**：AI 逻辑独立部署、独立发版、独立扩缩容。
4. **资源隔离**：AI 服务可单独限流/限内存，避免拖垮核心。

### 4.3 数据访问方式（优先级）

1. **Plane REST API**（首选）：使用服务账号 API Key（`X-API-Key`），官方稳定、有权限模型。
2. **MCP server**（可选）：让外部 AI 客户端也能操作 Plane。
3. **Webhooks**（辅助）：增量同步/触发。

### 4.4 前端集成方式

- **方式 A（推荐，最小侵入）**：在 `apps/web` 中新增一个 AI 面板组件，调用 AI Gateway。改动隔离在新增目录，便于与上游 merge。
- **方式 B（零 fork）**：独立 Web 组件（iframe / 独立子域），完全不动 Plane 前端。

> 初期推荐 **方式 A**（体验最好），但把代码集中在 `apps/web/core/components/ai/**` 与 `core/services/ai/**`，保持边界清晰。

---

## 5. 分阶段计划

### Phase 0：基础设施与准备（2–3 天）

**目标**：搭好可开发、可部署的地基。

**交付物**
- 仓库 fork 到 `aidai524/team`，建立分支策略。
- AI 专用 Postgres 库 + `pgvector` 扩展。
- DeepSeek API Key（或等价 provider key）。
- AI Gateway 服务骨架（FastAPI + Dockerfile + compose 片段）。
- 反向代理路由 `/ai/*` → AI Gateway。
- Plane 服务账号 + API Key（用于工具层读写）。

**验收标准**
- `curl https://team.stableflow.ai/ai/health` 返回 200。
- Gateway 能通过 API Key 读取 Plane 的一个工作区。

---

### Phase 1：基础问答助手（MVP）（3–5 天）

**目标**：能用自然语言问工作区数据，只读。

**交付物**
- AI Gateway：`/chat` 接口（SSE 流式）。
- LLM Adapter：DeepSeek（OpenAI 兼容）+ 模型白名单扩展。
- 前端 AI 聊天面板（侧边滑出 + 全屏）。
- 只读工具：List/Get `projects`、`work_items`、`cycles`、`modules`、`pages`、`members`、`states`。
- 会话持久化（Postgres）。

**验收标准**
- 问「哪些高优先级工作项还没分配？」能返回真实数据。
- 问「总结本周后端项目完成了什么？」能给出汇总。
- 响应流式输出，首个 token < 3s。

---

### Phase 2：工具调用 / Agent（读 + Build 模式确认写）（2–3 周）

**目标**：AI 能规划并执行写操作，且必须人工确认。

**交付物**
- Agent 编排：多轮 tool calling（function calling）。
- **三种模式**：Ask（只读）/ Build（计划→确认→执行）/ Autopilot（直接执行）。
- **动作卡片 UI**：展示将要执行的操作，可编辑/取消/逐条确认。
- 写工具：创建/更新工作项、指派、打标签、评论、移入周期/模块、创建周期/模块/页面。
- 执行结果汇总（成功/失败 + 跳转链接）。
- 审计日志（谁、在何时、让 AI 做了什么）。

**验收标准**
- 「在 mobile 项目把所有未分配的高优先级工作项指派给 @alice」→ 生成动作卡片 → 确认后正确执行。
- 未确认时工作区零变更。
- 每个写操作可追溯到发起人。

---

### Phase 3：检索增强（RAG / 语义搜索）（1–2 周）

**目标**：从「结构化查询」升级到「语义检索」，支持跨工作项/页面的模糊提问。

**交付物**
- Embedding 生成（DeepSeek/BGE/OpenAI 均可）+ `pgvector` 存储。
- 索引任务：工作项、评论、页面内容（增量同步）。
- 混合检索（向量 + 关键词 + 结构化过滤）。
- 引用来源展示（回答标注出处与链接）。

**验收标准**
- 「有没有关于登录流程卡点的讨论？」能召回相关评论/页面。
- 回答附带可点击的来源链接。

---

### Phase 4：页面编辑器 AI（2–3 周）

**目标**：把 AI 深度嵌入文档编辑，体验对齐商业版。

**交付物**
- 顶部 AI 输入框：自由指令 → 流式写入（`Thinking...` / `Persisting...` 状态）。
- **逐块 proposal**：生成内容以提案形式高亮，支持逐块 Accept / Reject、Accept all / Reject all、键盘快捷键。
- 选区改写：Paraphrase / Simplify / Elaborate / Summarize / Get title + 语气切换。
- AI block：插入内容块并用 prompt 生成。
- 后端补齐 `rephrase-grammar` 类接口。

**验收标准**
- 「在开头写一段执行摘要」能流式写入且逐块可控。
- 选区改写可替换/追加/重生，原文在被拒时保持不变。

---

### Phase 5：AI Skills + MCP（2–3 周）

**目标**：可复用能力 + 外部上下文接入。

**交付物**
- **AI Skills**：保存指令模板，斜杠命令 `/name` 调用，支持 `{{变量}}`，作用域 Personal / Workspace。
- **MCP 客户端**：接入 GitHub / Sentry / Granola 等（每人独立授权，token 加密）。
- 仅 Build / Autopilot 模式启用动作型连接器。

**验收标准**
- 保存 `/weekly-update` 技能，运行时可填变量并生成结果。
- 连接 GitHub 后，AI 能引用 PR 信息。

---

### Phase 6：用量、权限、打磨（1–2 周）

**目标**：可运营、可治理。

**交付物**
- 用量统计（工作区/成员维度）、限额与告警。
- 权限：Guest 不可用；工作区级 AI 总开关。
- 可观测性：日志、追踪、错误率、延迟。
- 模型切换、语音输入、文件上传（可选）。
- 文档与运维手册。

**验收标准**
- 管理端能看到用量与限额。
- Guest 用户无法访问 AI。

---

## 6. 技术栈

| 层 | 选型 |
| --- | --- |
| AI 服务 | Python 3.12 + FastAPI（与 Plane 后端同栈，复用经验） |
| LLM | DeepSeek（OpenAI 兼容），可切换 OpenAI / Anthropic |
| 向量库 | Postgres 15 + pgvector |
| Embedding | DeepSeek / BGE / OpenAI（可插拔） |
| 前端 | React Router + MobX（复用 Plane 现有栈与组件库 `@plane/ui` / `propel`） |
| 队列 | 复用现有 RabbitMQ（索引/长任务） |
| 部署 | Docker Compose（新增服务），反向代理复用 Caddy |
| 观测 | 结构化日志 + 请求追踪（OpenTelemetry 可选） |

---

## 7. 仓库结构与分支策略

```
team/
├── apps/                      # Plane 原有（尽量不改核心）
│   └── web/core/components/ai/   # 新增：前端 AI 面板（隔离目录）
├── ai/                        # 新增：AI Gateway 服务
│   ├── app/
│   │   ├── main.py
│   │   ├── api/               # chat / skills / usage
│   │   ├── agent/             # orchestrator、tools
│   │   ├── llm/               # provider adapters
│   │   ├── retrieval/         # pgvector RAG
│   │   └── plane/             # Plane REST 客户端
│   ├── Dockerfile
│   └── pyproject.toml
├── deployments/ai/            # AI 服务的 compose 片段与配置模板
└── docs/ai-features-plan.md   # 本文档
```

**分支策略**

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定基线（跟随上游可用版本） |
| `sync/upstream` | 定期同步 `makeplane/plane` 上游 |
| `feat/ai-*` | 各 Phase 特性分支 |
| `release/*` | 发布分支 |

**同步上游原则**：核心改动越少越好，AI 相关代码集中在 `ai/` 与 `apps/web/core/**/ai/`，降低 merge 冲突。

---

## 8. 里程碑

| 阶段 | 内容 | 预估工期 | 累计 |
| --- | --- | --- | --- |
| Phase 0 | 基础设施与准备 | 2–3 天 | ~0.5 周 |
| Phase 1 | 基础问答（MVP） | 3–5 天 | ~1.5 周 |
| Phase 2 | 工具调用 / Agent | 2–3 周 | ~4.5 周 |
| Phase 3 | 检索增强（RAG） | 1–2 周 | ~6.5 周 |
| Phase 4 | 页面编辑器 AI | 2–3 周 | ~9.5 周 |
| Phase 5 | AI Skills + MCP | 2–3 周 | ~12.5 周 |
| Phase 6 | 用量 / 权限 / 打磨 | 1–2 周 | ~14 周 |

> 以 1 名全职工程师估算，约 **3 个月**达到「接近商业版核心体验」。

---

## 9. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 服务器资源不足 | AI 服务/索引拖垮主服务 | 用 pgvector 替代 OpenSearch；必要时升配到 4C/8G |
| 上游升级冲突 | 维护成本高 | 核心零改动，AI 独立目录/独立服务 |
| LLM 幻觉误操作 | 数据被改错 | Build 模式强制人工确认；审计日志；可撤销设计 |
| 权限越权 | 数据泄露 | 复用 Plane 权限，API 按发起人身份/最小权限 |
| AGPL 合规 | 法律风险 | AI 独立服务 + 公开 API；对外服务时开源 |
| 成本失控 | LLM 费用超支 | 用量统计 + 限额 + 模型分级（简单任务用小模型） |
| 模型白名单限制 | DeepSeek 无法直接用 | 自定义 provider / 白名单扩展（Phase 1 解决） |

---

## 10. 合规检查清单

- [ ] 不复制商业版代码
- [ ] 不使用官方商标命名
- [ ] AI 服务与核心解耦（独立进程 + 公开 API）
- [ ] 保留所有 AGPL 版权与许可证声明
- [ ] 若对外提供网络服务，准备开源修改后的源码
- [ ] 用户数据处理与隐私说明（发送给 LLM 的数据范围）

---

## 11. 附录：当前部署速查

| 项 | 值 |
| --- | --- |
| 站点 | `https://team.stableflow.ai` |
| 版本 | Plane Community `v1.4.2` |
| 部署目录 | `/root/plane-selfhost/` |
| 配置 | `/root/plane-selfhost/plane-app/plane.env` |
| 管理命令 | `./setup.sh start\|stop\|restart\|logs\|backup\|upgrade` |
| SSL | Caddy + Let's Encrypt（自动续期） |
| 邮件 | Resend SMTP，发件人 `no-reply@mailserver.stableflow.ai` |
| 数据库 | Postgres 15.7（容器 `plane-app-plane-db-1`） |

> ⚠️ 安全提醒：`plane.env` 含数据库密码、`SECRET_KEY`、Resend API Key 等敏感信息，**严禁提交到仓库**。
