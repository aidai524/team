"use client";

import { useEffect } from "react";
import { observer } from "mobx-react";
import { PlusIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";

type Props = {
  workspaceSlug: string;
  onOpenConversation: (conversationId: string) => void;
};

export const AIChatSessions = observer(function AIChatSessions({ workspaceSlug, onOpenConversation }: Props) {
  const chat = useAIChat();

  useEffect(() => {
    void chat.loadSessions(workspaceSlug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceSlug]);

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3">
      <button
        type="button"
        onClick={chat.newConversation}
        className="flex w-full items-center justify-center gap-1.5 rounded-md border border-subtle px-2 py-1.5 text-13 text-secondary hover:bg-layer-1 hover:text-primary"
      >
        <PlusIcon className="size-3.5" />
        新对话
      </button>

      <div className="mt-3 space-y-1">
        {chat.sessions.length === 0 && <p className="px-2 text-13 text-tertiary">暂无历史会话</p>}
        {chat.sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => onOpenConversation(session.id)}
            className={cn(
              "block w-full truncate rounded-md px-2 py-1.5 text-left text-13",
              chat.conversationId === session.id
                ? "bg-layer-1 text-primary"
                : "text-secondary hover:bg-layer-1 hover:text-primary"
            )}
          >
            {session.title || "未命名会话"}
          </button>
        ))}
      </div>
    </div>
  );
});
