"use client";

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { CloseIcon } from "@plane/propel/icons";
// hooks
import { useAIChat } from "@/hooks/store/use-ai-chat";

export const AIChatSkills = observer(function AIChatSkills({ workspaceSlug }: { workspaceSlug: string }) {
  const chat = useAIChat();
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void chat.loadSkills(workspaceSlug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceSlug]);

  const submit = async () => {
    if (!name.trim() || !prompt.trim() || saving) return;
    setSaving(true);
    try {
      await chat.addSkill(workspaceSlug, name.trim(), prompt.trim());
      setName("");
      setPrompt("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3">
      <div className="space-y-2 rounded-md border border-subtle bg-layer-1 p-2">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="技能名称（如 weekly-update）"
          className="w-full rounded-md border border-subtle bg-surface-1 px-2 py-1.5 text-13 text-primary placeholder:text-tertiary outline-none"
        />
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          placeholder="指令模板，支持 {{变量}}，如：生成 {{project}} 的周报"
          className="w-full resize-none rounded-md border border-subtle bg-surface-1 px-2 py-1.5 text-13 text-primary placeholder:text-tertiary outline-none"
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={!name.trim() || !prompt.trim() || saving}
          className="w-full rounded-md bg-accent-primary px-2 py-1.5 text-13 font-medium text-on-color disabled:opacity-50"
        >
          {saving ? "保存中…" : "保存技能"}
        </button>
      </div>

      <div className="mt-3 space-y-2">
        {chat.skills.length === 0 && <p className="px-2 text-13 text-tertiary">暂无技能，创建后可在输入框用 /名称 调用</p>}
        {chat.skills.map((skill) => (
          <div key={skill.id} className="rounded-md border border-subtle bg-surface-1 p-2">
            <div className="flex items-center justify-between">
              <span className="text-13 font-medium text-primary">/{skill.name}</span>
              <button
                type="button"
                onClick={() => void chat.removeSkill(skill.id, workspaceSlug)}
                aria-label="删除技能"
                className="grid size-5 place-items-center rounded text-tertiary hover:text-danger-primary"
              >
                <CloseIcon className="size-3.5" />
              </button>
            </div>
            <pre className="mt-1 whitespace-pre-wrap text-11 text-tertiary">{skill.prompt}</pre>
          </div>
        ))}
      </div>
    </div>
  );
});
