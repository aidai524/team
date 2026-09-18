"use client";

import { useEffect, useRef } from "react";
import { observer } from "mobx-react";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";
// components
import { AIChatMessage } from "./message";

export const AIChatMessageList = observer(function AIChatMessageList() {
  const chat = useAIChat();
  const endRef = useRef<HTMLDivElement>(null);
  const lastMessage = chat.messages[chat.messages.length - 1];

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages.length, lastMessage?.content.length]);

  if (chat.messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm text-secondary">向 AI 询问你的工作区数据</p>
        <p className="text-13 text-tertiary">例如：哪些高优先级工作项还没分配？</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {chat.messages.map((message) => (
        <AIChatMessage key={message.id} message={message} />
      ))}
      {chat.error && <p className="text-13 text-danger-primary">{chat.error}</p>}
      <div ref={endRef} />
    </div>
  );
});
