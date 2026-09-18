"use client";

import { observer } from "mobx-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
          "max-w-[85%] rounded-md px-3 py-2 text-sm",
          isUser ? "whitespace-pre-wrap bg-layer-1 text-primary" : "text-primary"
        )}
      >
        {message.content ? (
          isUser ? (
            message.content
          ) : (
            <div className="space-y-2 [&_a]:text-accent-primary [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-subtle [&_blockquote]:pl-3 [&_blockquote]:text-tertiary [&_code]:rounded [&_code]:bg-layer-1 [&_code]:px-1 [&_code]:py-0.5 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-2 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-medium [&_hr]:border-subtle [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-layer-1 [&_pre]:p-2 [&_strong]:font-semibold [&_table]:my-1 [&_table]:w-full [&_table]:border-collapse [&_table]:text-12 [&_td]:border [&_td]:border-subtle [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-subtle [&_th]:bg-layer-1 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-medium [&_ul]:list-disc [&_ul]:pl-5">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )
        ) : showStreaming ? (
          <span className="text-tertiary">思考中…</span>
        ) : null}
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
