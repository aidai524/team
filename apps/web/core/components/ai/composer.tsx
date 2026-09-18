"use client";

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { cn } from "@plane/utils";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";
// types
import type { TAIChatMode } from "@/services/ai/ai-gateway.service";

const MODES: { value: TAIChatMode; label: string }[] = [
  { value: "ask", label: "问答" },
  { value: "build", label: "执行" },
];

export const AIChatComposer = observer(function AIChatComposer({ workspaceSlug }: { workspaceSlug: string }) {
  const chat = useAIChat();
  const [value, setValue] = useState("");

  useEffect(() => {
    void chat.loadSkills(workspaceSlug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceSlug]);

  const canSend = value.trim().length > 0 && !chat.isStreaming;
  const matchingSkills = value.startsWith("/")
    ? chat.skills.filter((s) => s.name.toLowerCase().startsWith(value.slice(1).toLowerCase())).slice(0, 6)
    : [];

  const submit = () => {
    if (!canSend) return;
    const text = value;
    setValue("");
    void chat.sendMessage(text, workspaceSlug);
  };

  const insertSkill = (name: string) => {
    setValue(`/${name} `);
  };

  return (
    <div className="border-t border-subtle p-3">
      {matchingSkills.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {matchingSkills.map((skill) => (
            <button
              key={skill.id}
              type="button"
              onClick={() => insertSkill(skill.name)}
              className="rounded-sm border border-subtle px-2 py-0.5 text-12 text-secondary hover:bg-layer-1"
            >
              /{skill.name}
            </button>
          ))}
        </div>
      )}
      <div className="mb-2 flex items-center gap-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => chat.setMode(m.value)}
            className={cn(
              "rounded-sm px-2 py-0.5 text-12",
              chat.mode === m.value ? "bg-accent-subtle text-accent-secondary" : "text-tertiary hover:text-primary"
            )}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder={chat.mode === "build" ? "描述要执行的操作，AI 会先生成计划…" : "向 AI 提问…"}
          className="flex-1 resize-none rounded-md border border-subtle bg-layer-2 px-3 py-2 text-sm text-primary placeholder:text-tertiary outline-none focus:border-accent-strong-200"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          className="rounded-md bg-accent-primary px-3 py-2 text-sm font-medium text-on-color disabled:opacity-50"
        >
          {chat.mode === "build" ? "生成计划" : "发送"}
        </button>
      </div>
    </div>
  );
});
