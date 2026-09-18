# AI Gateway 部署片段

本目录提供 Phase 0 的部署模板，用于把 AI Gateway 接入 Plane 社区版
Docker Compose 栈。

## 文件

| 文件 | 用途 |
| --- | --- |
| `docker-compose.ai.yml` | AI Gateway + pgvector 数据库的 compose overlay 片段 |
| `plane-ai.env.example` | 环境变量模板，复制为 `plane-ai.env` 并填密钥 |
| 本 README | 部署步骤 |

## 部署步骤（仓库根目录）

1. 准备密钥：

   ```bash
   cp deployments/ai/plane-ai.env.example deployments/ai/plane-ai.env
   # 编辑 plane-ai.env，填写：
   #   AI_GATEWAY_GATEWAY_API_KEY  (openssl rand -hex 32)
   #   AI_GATEWAY_PLANE_API_KEY    (Plane 服务账号 API token)
   #   AI_GATEWAY_LLM_API_KEY      (DeepSeek key)
   #   AI_DB_PASSWORD
   ```

2. 启动（overlay 方式，复用主栈网络）：

   ```bash
   docker compose -f docker-compose.yml -f deployments/ai/docker-compose.ai.yml up -d --build
   ```

3. 验证：

   ```bash
   curl -s https://team.stableflow.ai/ai/health
   # {"status":"ok","version":"0.1.0"}
   curl -s https://team.stableflow.ai/ai/ready
   # {"status":"ready","plane_user":"..."}
   ```

## 说明

- **反向代理**：`apps/proxy/Caddyfile.ce` 已新增 `handle_path /ai/*`，
  把 `/ai/*` 剥掉前缀转发到 `plane-ai:8000`，并服务端注入
  `X-AI-Gateway-Key` 头（值来自 `AI_GATEWAY_KEY`）。
- **密钥关系**：`AI_GATEWAY_KEY`（Caddy/proxy 环境）与 `plane-ai.env` 里的
  `AI_GATEWAY_GATEWAY_API_KEY` 必须**一致**。浏览器不接触该密钥。
  本地直连调试时，可改由前端 `VITE_AI_GATEWAY_KEY` 携带。
- **⚠️ 依赖顺序**：Caddy 会在启动时解析 `plane-ai` 上游；必须先启动
  `plane-ai`（或保证该主机名可解析），否则 proxy 容器会启动失败。
  回滚方式：从 Caddyfile 删除 `handle_path /ai/*` 块并重启 proxy。
- **相对路径**：compose 片段内相对路径基于片段文件所在目录解析
  （Compose v2），`../../ai` 指向仓库根的 `ai/`，`./plane-ai.env` 指向本目录。
- **pgvector**：`plane-ai-db` 供 Phase 3 检索使用，Phase 0/1 可先不接。
- 生产环境请勿在 `plane-ai.env` 留空密钥；该文件含敏感信息，**不要提交**。
