"use client";

import { observer } from "mobx-react";
import { CheckIcon, CloseIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";

export const AIChatActionResults = observer(function AIChatActionResults() {
  const chat = useAIChat();

  if (chat.executionResults.length === 0) return null;

  return (
    <div className="border-t border-subtle bg-layer-1 px-4 py-3">
      <div className="mb-2 text-13 font-medium text-secondary">执行结果</div>
      <div className="space-y-2">
        {chat.executionResults.map((result, index) => (
          <div
            key={`${result.action}-${index}`}
            className={cn(
              "flex items-start gap-2 rounded-md border p-2 text-13",
              result.ok ? "border-subtle bg-surface-1" : "border-danger-subtle bg-surface-1"
            )}
          >
            {result.ok ? (
              <CheckIcon className="mt-0.5 size-4 shrink-0 text-accent-primary" />
            ) : (
              <CloseIcon className="mt-0.5 size-4 shrink-0 text-danger-primary" />
            )}
            <div className="min-w-0 flex-1">
              <div className="font-medium text-primary">{result.action}</div>
              {result.ok ? (
                <div className="text-tertiary">
                  {result.sequence_id ? `${result.sequence_id} · ` : ""}
                  {result.name ?? result.id ?? "完成"}
                </div>
              ) : (
                <div className="text-danger-primary">{result.error ?? "失败"}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
