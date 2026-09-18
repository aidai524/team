"use client";

import { observer } from "mobx-react";
import { cn } from "@plane/utils";
// types
import type { TAIChatMessage } from "@/services/ai/ai-gateway.service";

export const AIChatMessage = observer(function AIChatMessage({ message }: { message: TAIChatMessage }) {
  const isUser = message.role === "user";
  const showStreaming = message.isStreaming && !message.content;

  if (!message.content && !message.isStreaming) return null;

  return (
    <div className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm",
          isUser ? "bg-layer-1 text-primary" : "text-primary"
        )}
      >
        {message.content || (showStreaming ? <span className="text-tertiary">思考中…</span> : null)}
      </div>
      {message.toolActivity && message.toolActivity.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {message.toolActivity.map((name) => (
            <span key={name} className="rounded-sm border border-subtle px-1.5 py-0.5 text-11 text-tertiary">
              {name}
            </span>
          ))}
        </div>
      )}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-1 space-y-0.5">
          {message.sources.map((source, index) => (
            <a
              key={`${source.link}-${index}`}
              href={source.link ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="block text-12 text-accent-primary hover:underline"
            >
              {source.title ?? source.name ?? "来源"}
            </a>
          ))}
        </div>
      )}
    </div>
  );
});
