"use client";

import { useState } from "react";
import { observer } from "mobx-react";
import { AiIcon, CloseIcon, FullScreenPanelIcon, PlusIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";
// components
import { AIChatActionPlan } from "./action-plan";
import { AIChatActionResults } from "./action-results";
import { AIChatComposer } from "./composer";
import { AIChatMessageList } from "./message-list";
import { AIChatSessions } from "./ai-sessions";
import { AIChatSkills } from "./ai-skills";
import { AIChatUsage } from "./ai-usage";

type PanelView = "chat" | "history" | "skills" | "usage";

const TABS: { key: PanelView; label: string }[] = [
  { key: "chat", label: "对话" },
  { key: "history", label: "历史" },
  { key: "skills", label: "技能" },
  { key: "usage", label: "用量" },
];

export const AIChatPanel = observer(function AIChatPanel({ workspaceSlug }: { workspaceSlug: string }) {
  const chat = useAIChat();
  const [view, setView] = useState<PanelView>("chat");

  const openConversation = (conversationId: string) => {
    void chat.loadConversation(conversationId);
    setView("chat");
  };

  return (
    <>
      <button
        type="button"
        onClick={chat.toggle}
        aria-label="AI 助手"
        className="fixed bottom-6 right-6 z-[40] grid size-12 place-items-center rounded-full bg-accent-primary text-on-color shadow-lg transition-transform hover:scale-105"
      >
        <AiIcon className="size-6" />
      </button>

      {chat.isOpen && (
        <div
          className={cn(
            "fixed inset-y-0 right-0 z-[50] flex flex-col bg-surface-1 border-l border-subtle shadow-2xl",
            chat.isFullScreen ? "inset-x-0 border-l-0" : "w-[400px] max-w-full"
          )}
        >
          <div className="flex items-center justify-between border-b border-subtle px-4 py-3">
            <div className="flex items-center gap-2">
              <AiIcon className="size-5 text-accent-primary" />
              <span className="text-sm font-medium text-primary">AI 助手</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={chat.newConversation}
                aria-label="新对话"
                className="grid size-7 place-items-center rounded-md text-tertiary hover:bg-layer-1 hover:text-primary"
              >
                <PlusIcon className="size-4" />
              </button>
              <button
                type="button"
                onClick={chat.toggleFullScreen}
                aria-label="全屏"
                className="grid size-7 place-items-center rounded-md text-tertiary hover:bg-layer-1 hover:text-primary"
              >
                <FullScreenPanelIcon className="size-4" />
              </button>
              <button
                type="button"
                onClick={chat.close}
                aria-label="关闭"
                className="grid size-7 place-items-center rounded-md text-tertiary hover:bg-layer-1 hover:text-primary"
              >
                <CloseIcon className="size-4" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-1 border-b border-subtle px-3 py-1.5">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setView(tab.key)}
                className={cn(
                  "rounded-sm px-2 py-1 text-12",
                  view === tab.key ? "bg-accent-subtle text-accent-secondary" : "text-tertiary hover:text-primary"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {view === "chat" && (
            <>
              <AIChatMessageList />
              <AIChatActionResults />
              <AIChatActionPlan workspaceSlug={workspaceSlug} />
              <AIChatComposer workspaceSlug={workspaceSlug} />
            </>
          )}
          {view === "history" && <AIChatSessions workspaceSlug={workspaceSlug} onOpenConversation={openConversation} />}
          {view === "skills" && <AIChatSkills workspaceSlug={workspaceSlug} />}
          {view === "usage" && <AIChatUsage workspaceSlug={workspaceSlug} />}
        </div>
      )}
    </>
  );
});
