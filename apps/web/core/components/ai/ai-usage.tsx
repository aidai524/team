"use client";

import { useEffect } from "react";
import { observer } from "mobx-react";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";

export const AIChatUsage = observer(function AIChatUsage({ workspaceSlug }: { workspaceSlug: string }) {
  const chat = useAIChat();

  useEffect(() => {
    void chat.loadUsage(workspaceSlug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceSlug]);

  const usage = chat.usage;

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      <div className="rounded-md border border-subtle bg-layer-1 p-3">
        <div className="text-13 text-secondary">总请求数</div>
        <div className="mt-1 text-18 font-medium text-primary">{usage?.totalRequests ?? 0}</div>
      </div>
      <div className="rounded-md border border-subtle bg-layer-1 p-3">
        <div className="text-13 text-secondary">平均延迟</div>
        <div className="mt-1 text-18 font-medium text-primary">{usage ? `${usage.avgLatencyMs} ms` : "-"}</div>
      </div>
      <div className="rounded-md border border-subtle bg-layer-1 p-3">
        <div className="text-13 text-secondary">累计耗时</div>
        <div className="mt-1 text-18 font-medium text-primary">{usage ? `${usage.totalLatencyMs} ms` : "-"}</div>
      </div>
    </div>
  );
});
