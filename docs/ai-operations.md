# AI Gateway 运维手册

> 适用：Plane 社区版（AGPL-3.0）自托管 + 独立 AI Gateway（本仓库 `ai/`）。
> 完整路线图见 `docs/ai-features-plan.md`。

## 1. 部署

### 1.1 前置

- 仓库已 fork（`aidai524/team`），AI 代码集中在 `ai/`、`apps/web/core/**/ai/`、`deployments/ai/`。
- DeepSeek（或 OpenAI 兼容）LLM key。
- Embedding 端点（可选；OpenAI 兼容 `/embeddings`，或自建 BGE/TEI/infinity）。
- Plane 服务账号 API token（用于工具层读写）。

### 1.2 首次部署

```bash
# 1. 准备密钥（敏感，勿提交）
cp deployments/ai/plane-ai.env.example deployments/ai/plane-ai.env
# 编辑：AI_GATEWAY_GATEWAY_API_KEY / AI_GATEWAY_PLANE_API_KEY / AI_GATEWAY_LLM_API_KEY / AI_DB_PASSWORD

# 2. 根 .env 增加 AI_GATEWAY_KEY（与上面 GATEWAY_API_KEY 一致，Caddy 服务端注入用）

# 3. 启动（overlay，复用主栈网络）
docker compose -f docker-compose.yml -f deployments/ai/docker-compose.ai.yml up -d --build

# 4. 验证
curl -s https://team.stableflow.ai/ai/health   # {"status":"ok",...}
curl -s https://team.stableflow.ai/ai/ready    # {"status":"ready","plane_user":...}
```

### 1.3 升级 / 回滚

- 升级：`docker compose -f ... up -d --build plane-ai`（AI 服务独立发版，不影响 Plane 核心）。
- 回滚反向代理：从 `apps/proxy/Caddyfile.ce` 删除 `handle_path /ai/*` 块，重启 proxy。

## 2. 配置参考

环境变量前缀 `AI_GATEWAY_`，见 `ai/.env.example` 与 `deployments/ai/plane-ai.env.example`。要点：

| 变量 | 说明 |
| --- | --- |
| `AI_GATEWAY_PLANE_API_KEY` | Plane 服务账号 token（工具层） |
| `AI_GATEWAY_LLM_PROVIDER/MODEL/BASE_URL/API_KEY` | DeepSeek/OpenAI 兼容 |
| `AI_GATEWAY_GATEWAY_API_KEY` | 网关自身共享密钥（Caddy 服务端注入） |
| `AI_GATEWAY_DATABASE_URL` | `postgresql+asyncpg://...@plane-ai-db:5432/plane_ai` |
| `AI_GATEWAY_EMBEDDING_*` | 向量检索；key 为空则纯关键词检索 |
| `AI_GATEWAY_RETRIEVAL_TOP_K` | 检索 top-k（默认 5） |

## 3. 接口速查

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/ai/health` | 存活 |
| GET | `/ai/ready` | 就绪（验证 Plane key） |
| POST | `/ai/chat` | 对话（SSE；mode=ask/build/autopilot） |
| POST | `/ai/execute` | 执行确认后的写动作 |
| POST | `/ai/retrieval/index` | 增量索引工作区 |
| POST | `/ai/editor/task` | 选区改写（非流式） |
| POST | `/ai/editor/ask` | 自由指令改写（非流式） |
| POST | `/ai/editor/stream` | 编辑器流式写入 |
| GET/POST/DELETE | `/ai/skills` | 斜杠命令技能 |
| GET/POST/DELETE | `/ai/mcp` | MCP 连接管理 |
| GET | `/ai/usage` | 用量统计 |
| GET/PUT | `/ai/settings/ai` | 工作区 AI 开关 |
| GET | `/ai/sessions` | 会话列表 |

> 网关暴露路径为 `/health` 等；Caddy `handle_path /ai/*` 剥前缀后转发，所以对外是 `/ai/health`。

## 4. 日常运维

### 4.1 索引

- 触发：`curl -X POST https://team.stableflow.ai/ai/retrieval/index -H 'Content-Type: application/json' -d '{"workspace_slug":"<slug>"}'`
- 增量：只重新嵌入 `updated_at` 变化的文档，返回 `{indexed, skipped, projects}`。
- 建议：用 cron 定时触发（如每 10 分钟），后续可迁到 RabbitMQ 队列。

### 4.2 用量 / 审计 / 权限

- 用量：`GET /ai/usage?workspace_slug=<slug>`（请求数/平均延迟）。
- 审计：每次 `/execute` 写 `audit_logs`（action/params/status/result/时间）。
- 权限：`PUT /ai/settings/ai {"workspace_slug","ai_enabled":false}` 关闭工作区 AI（Guest 限制需按用户鉴权落地后生效）。

### 4.3 可观测性

- 结构化日志：`AI_GATEWAY_LOG_LEVEL=INFO`，每请求打印 method/path/status/耗时 + `X-Request-Id`。
- 容器日志：`docker compose logs -f plane-ai`。

## 5. 故障排查

| 现象 | 排查 |
| --- | --- |
| `/ai/health` 502/504 | `plane-ai` 容器未起/网络不通；`docker compose logs plane-ai` |
| Caddy 启动失败 | 确认 `plane-ai` 主机名可解析（先起 AI 服务再起 proxy） |
| `/ai/ready` 503 | `AI_GATEWAY_PLANE_API_KEY` 无效或 Plane API 不可达 |
| chat 返回 401 | Caddy `AI_GATEWAY_KEY` 与 `AI_GATEWAY_GATEWAY_API_KEY` 不一致 |
| chat 返回 403 | 该工作区 AI 被关闭（`/ai/settings/ai`） |
| 检索无结果 | 未索引；确认 embedding key 或先触发索引 |

## 6. 安全

- `plane-ai.env`、根 `.env` 含敏感信息，**严禁提交**（已在 `.gitignore`）。
- 浏览器不接触网关密钥（Caddy 服务端注入）。
- MCP token 目前明文存 `mcp_connections.config_json`，**加密存储是后续项**。
- 对外提供网络服务时，需遵守 AGPL §13 提供修改后源码（见计划 §10 合规清单）。
