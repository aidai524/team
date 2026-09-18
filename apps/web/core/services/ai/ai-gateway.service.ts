/**
 * AI Gateway client (SSE streaming + session APIs).
 *
 * Talks to the independent AI Gateway mounted at `/ai/*` (Caddy strips the
 * prefix). In production the gateway key is injected by Caddy server-side; in
 * local dev set VITE_AI_GATEWAY_URL / VITE_AI_GATEWAY_KEY.
 */

export type TAIGatewayEventType = "token" | "tool_call" | "tool_result" | "plan" | "sources" | "done" | "error";

export type TAIProposedAction = {
  action: string;
  params: Record<string, unknown>;
};

export type TAISource = {
  title?: string;
  name?: string;
  link?: string;
  snippet?: string;
};

export type TAIGatewayEvent = {
  type: TAIGatewayEventType;
  content?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  result?: string;
  actions?: TAIProposedAction[];
  sources?: TAISource[];
  conversationId?: string;
  message?: string;
};

export type TAIExecutionResult = {
  action: string;
  ok: boolean;
  id?: string;
  sequence_id?: string;
  name?: string;
  link?: string;
  error?: string;
};

export type TAIChatMode = "ask" | "build" | "autopilot";

export type TAIChatRole = "user" | "assistant";

export type TAIChatMessage = {
  id: string;
  role: TAIChatRole;
  content: string;
  isStreaming?: boolean;
  /** Tool names the agent invoked while producing this answer. */
  toolActivity?: string[];
  /** Sources cited by the retrieval tool. */
  sources?: TAISource[];
};

export type TAISession = {
  id: string;
  title: string | null;
  workspaceSlug: string | null;
  updatedAt: string | null;
};

export type TAISessionMessage = {
  role: TAIChatRole;
  content: string;
};

const GATEWAY_URL = process.env.VITE_AI_GATEWAY_URL || "/ai";
const GATEWAY_KEY = process.env.VITE_AI_GATEWAY_KEY || "";

function headers(): Record<string, string> {
  const result: Record<string, string> = { "Content-Type": "application/json" };
  if (GATEWAY_KEY) result["X-AI-Gateway-Key"] = GATEWAY_KEY;
  return result;
}

function parseSSEChunk(chunk: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

function safeJson(data: string): Record<string, any> | null {
  try {
    const parsed = JSON.parse(data);
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

function mapEvent(event: string, data: string): TAIGatewayEvent {
  switch (event) {
    case "token":
      return { type: "token", content: data };
    case "tool_call": {
      const parsed = safeJson(data);
      return { type: "tool_call", name: parsed?.name, arguments: parsed?.arguments };
    }
    case "tool_result": {
      const parsed = safeJson(data);
      return { type: "tool_result", name: parsed?.name, result: parsed?.result };
    }
    case "plan": {
      const parsed = safeJson(data);
      return { type: "plan", actions: Array.isArray(parsed?.actions) ? parsed.actions : [] };
    }
    case "sources": {
      const parsed = safeJson(data);
      return { type: "sources", sources: Array.isArray(parsed?.sources) ? parsed.sources : [] };
    }
    case "done": {
      const parsed = safeJson(data);
      return { type: "done", conversationId: parsed?.conversation_id };
    }
    case "error":
      return { type: "error", message: data };
    default:
      return { type: "token", content: data };
  }
}

export async function streamChat(
  body: { message: string; workspaceSlug: string; conversationId?: string | null; mode?: TAIChatMode },
  onEvent: (event: TAIGatewayEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${GATEWAY_URL}/chat`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      message: body.message,
      workspace_slug: body.workspaceSlug,
      conversation_id: body.conversationId ?? undefined,
      mode: body.mode ?? "ask",
    }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`AI gateway error ${response.status}: ${text.slice(0, 500)}`);
  }
  if (!response.body) throw new Error("AI gateway returned an empty body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (chunk: string) => {
    const parsed = parseSSEChunk(chunk);
    if (parsed) onEvent(mapEvent(parsed.event, parsed.data));
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) dispatch(chunk);
  }
  if (buffer.trim()) dispatch(buffer);
}

export async function fetchSessions(workspaceSlug: string): Promise<TAISession[]> {
  const response = await fetch(`${GATEWAY_URL}/sessions?workspace_slug=${encodeURIComponent(workspaceSlug)}`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
  const data = await response.json();
  return (data ?? []).map((item: any) => ({
    id: item.id,
    title: item.title,
    workspaceSlug: item.workspace_slug,
    updatedAt: item.updated_at,
  }));
}

export async function fetchSessionMessages(conversationId: string): Promise<TAISessionMessage[]> {
  const response = await fetch(`${GATEWAY_URL}/sessions/${encodeURIComponent(conversationId)}/messages`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
  const data = await response.json();
  return (data ?? []).map((item: any) => ({
    role: item.role === "user" ? "user" : "assistant",
    content: item.content ?? "",
  }));
}

export async function executeActions(body: {
  workspaceSlug: string;
  conversationId?: string | null;
  actions: TAIProposedAction[];
}): Promise<TAIExecutionResult[]> {
  const response = await fetch(`${GATEWAY_URL}/execute`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      workspace_slug: body.workspaceSlug,
      conversation_id: body.conversationId ?? undefined,
      actions: body.actions,
    }),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`AI gateway error ${response.status}: ${text.slice(0, 500)}`);
  }
  const data = await response.json();
  return data?.results ?? [];
}

export type TAISkill = {
  id: string;
  workspaceSlug: string | null;
  scope: "personal" | "workspace";
  name: string;
  description: string | null;
  prompt: string;
};

export async function fetchSkills(workspaceSlug: string): Promise<TAISkill[]> {
  const response = await fetch(`${GATEWAY_URL}/skills?workspace_slug=${encodeURIComponent(workspaceSlug)}`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
  const data = await response.json();
  return (data ?? []).map((item: any) => ({
    id: item.id,
    workspaceSlug: item.workspace_slug,
    scope: item.scope,
    name: item.name,
    description: item.description,
    prompt: item.prompt,
  }));
}

export async function createSkill(body: {
  workspaceSlug: string;
  name: string;
  prompt: string;
  description?: string;
  scope?: "personal" | "workspace";
}): Promise<void> {
  const response = await fetch(`${GATEWAY_URL}/skills`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      workspace_slug: body.workspaceSlug,
      name: body.name,
      prompt: body.prompt,
      description: body.description ?? null,
      scope: body.scope ?? "workspace",
    }),
  });
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
}

export async function deleteSkill(skillId: string, workspaceSlug: string): Promise<void> {
  const response = await fetch(
    `${GATEWAY_URL}/skills/${encodeURIComponent(skillId)}?workspace_slug=${encodeURIComponent(workspaceSlug)}`,
    { method: "DELETE", headers: headers() }
  );
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
}

export type TAIUsage = {
  workspaceSlug: string;
  totalRequests: number;
  totalLatencyMs: number;
  avgLatencyMs: number;
};

export async function fetchUsage(workspaceSlug: string): Promise<TAIUsage> {
  const response = await fetch(`${GATEWAY_URL}/usage?workspace_slug=${encodeURIComponent(workspaceSlug)}`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`AI gateway error ${response.status}`);
  const data = await response.json();
  return {
    workspaceSlug: data?.workspace_slug ?? workspaceSlug,
    totalRequests: data?.total_requests ?? 0,
    totalLatencyMs: data?.total_latency_ms ?? 0,
    avgLatencyMs: data?.avg_latency_ms ?? 0,
  };
}

export async function editorTask(body: {
  task: "paraphrase" | "simplify" | "elaborate" | "summarize" | "title";
  text: string;
  tone?: "default" | "formal" | "casual" | "professional";
}): Promise<string> {
  const response = await fetch(`${GATEWAY_URL}/editor/task`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ task: body.task, text: body.text, tone: body.tone ?? "default" }),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`AI gateway error ${response.status}: ${text.slice(0, 500)}`);
  }
  const data = await response.json();
  return data?.response ?? "";
}

export async function editorAsk(body: {
  instruction: string;
  text: string;
  tone?: "default" | "formal" | "casual" | "professional";
}): Promise<string> {
  const response = await fetch(`${GATEWAY_URL}/editor/ask`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ instruction: body.instruction, text: body.text, tone: body.tone ?? "default" }),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`AI gateway error ${response.status}: ${text.slice(0, 500)}`);
  }
  const data = await response.json();
  return data?.response ?? "";
}

export async function streamEditor(
  body: {
    text: string;
    instruction?: string;
    task?: "paraphrase" | "simplify" | "elaborate" | "summarize" | "title";
    tone?: "default" | "formal" | "casual" | "professional";
  },
  onToken: (delta: string) => void,
  signal?: AbortSignal
): Promise<string> {
  const response = await fetch(`${GATEWAY_URL}/editor/stream`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      text: body.text,
      instruction: body.instruction ?? undefined,
      task: body.task ?? undefined,
      tone: body.tone ?? "default",
    }),
    signal,
  });
  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");
    throw new Error(`AI gateway error ${response.status}: ${text.slice(0, 500)}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const parsed = parseSSEChunk(chunk);
      if (!parsed) continue;
      if (parsed.event === "token") {
        full += parsed.data;
        onToken(parsed.data);
      }
    }
  }
  return full;
}
