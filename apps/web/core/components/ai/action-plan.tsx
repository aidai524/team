"use client";

import { observer } from "mobx-react";
import { CheckIcon, CloseIcon } from "@plane/propel/icons";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";

export const AIChatActionPlan = observer(function AIChatActionPlan({ workspaceSlug }: { workspaceSlug: string }) {
  const chat = useAIChat();

  if (chat.proposedActions.length === 0) return null;

  return (
    <div className="border-t border-subtle bg-layer-1 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-13 font-medium text-secondary">执行计划（{chat.proposedActions.length}）</span>
        <button
          type="button"
          onClick={chat.cancelPlan}
          className="text-13 text-tertiary hover:text-danger-primary"
        >
          全部取消
        </button>
      </div>

      <div className="space-y-2">
        {chat.proposedActions.map((action, index) => (
          <div key={`${action.action}-${index}`} className="flex items-start gap-2 rounded-md border border-subtle bg-surface-1 p-2">
            <div className="min-w-0 flex-1">
              <div className="text-13 font-medium text-primary">{action.action}</div>
              <pre className="mt-1 whitespace-pre-wrap break-all text-11 text-tertiary">
                {JSON.stringify(action.params, null, 2)}
              </pre>
            </div>
            <button
              type="button"
              onClick={() => chat.removeAction(index)}
              aria-label="移除该操作"
              className="grid size-6 shrink-0 place-items-center rounded text-tertiary hover:text-danger-primary"
            >
              <CloseIcon className="size-3.5" />
            </button>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={() => void chat.confirmPlan(workspaceSlug)}
        disabled={chat.isExecuting}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-md bg-accent-primary px-3 py-2 text-sm font-medium text-on-color disabled:opacity-50"
      >
        <CheckIcon className="size-4" />
        {chat.isExecuting ? "执行中…" : "确认执行"}
      </button>
    </div>
  );
});
