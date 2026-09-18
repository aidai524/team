"use client";

import { useState } from "react";
import { AiIcon, CloseIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// editor
import type { EditorRefApi } from "@plane/editor";
// services
import { streamEditor } from "@/services/ai/ai-gateway.service";

type Status = "idle" | "thinking" | "writing" | "done";

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function textToHtml(text: string): string {
  return text
    .split("\n")
    .map((line) => `<p>${escapeHtml(line) || "<br>"}</p>`)
    .join("");
}

type Props = {
  editorRef: EditorRefApi | null;
};

export function PageEditorAIWriteBar({ editorRef }: Props) {
  const [open, setOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setInstruction("");
    setResult("");
    setStatus("idle");
    setError(null);
    setOpen(false);
  };

  const submit = async () => {
    const text = instruction.trim();
    if (!text || !editorRef || status === "thinking" || status === "writing") return;

    const context = (editorRef.getSelectedText() ?? editorRef.getMarkDown() ?? "").slice(0, 50_000);
    setStatus("thinking");
    setResult("");
    setError(null);

    try {
      await streamEditor({ text: context, instruction: text }, (delta) => {
        setResult((prev) => prev + delta);
        setStatus("writing");
      });
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("idle");
    }
  };

  const insert = () => {
    if (!result) return;
    editorRef?.insertText(textToHtml(result), false);
    reset();
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="AI 写入"
        className={cn(
          "grid size-8 place-items-center rounded-md border-[0.5px] border-strong text-tertiary hover:bg-surface-2 hover:text-primary",
          { "border-accent-strong-200 bg-accent-primary/10 text-accent-secondary": open }
        )}
      >
        <AiIcon className="size-4" />
      </button>

      {open && (
        <div className="absolute top-12 right-0 z-20 w-[420px] max-w-full rounded-md border border-subtle bg-surface-1 p-3 shadow-raised-200">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-13 font-medium text-primary">AI 写入</span>
            <button type="button" onClick={() => setOpen(false)} aria-label="关闭" className="text-tertiary hover:text-primary">
              <CloseIcon className="size-4" />
            </button>
          </div>

          {status === "idle" && (
            <div className="space-y-2">
              <textarea
                value={instruction}
                onChange={(event) => setInstruction(event.target.value)}
                rows={2}
                placeholder="描述要写什么，如：写一段项目执行摘要"
                className="w-full resize-none rounded-md border border-subtle bg-layer-2 px-2 py-1.5 text-13 text-primary placeholder:text-tertiary outline-none"
              />
              <button
                type="button"
                onClick={() => void submit()}
                disabled={!instruction.trim()}
                className="w-full rounded-md bg-accent-primary px-2 py-1.5 text-13 font-medium text-on-color disabled:opacity-50"
              >
                生成
              </button>
              {error && <p className="text-12 text-danger-primary">{error}</p>}
            </div>
          )}

          {(status === "thinking" || status === "writing") && (
            <div className="space-y-2">
              <p className="text-13 text-tertiary">{status === "thinking" ? "Thinking…" : "Persisting…"}</p>
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md border border-subtle bg-layer-1 p-2 text-12 text-secondary">
                {result}
              </pre>
            </div>
          )}

          {status === "done" && (
            <div className="space-y-2">
              <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-md border border-subtle bg-layer-1 p-2 text-12 text-secondary">
                {result}
              </pre>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={insert}
                  className="flex-1 rounded-md bg-accent-primary px-2 py-1.5 text-13 font-medium text-on-color"
                >
                  插入到光标处
                </button>
                <button
                  type="button"
                  onClick={reset}
                  className="rounded-md border border-subtle px-3 py-1.5 text-13 text-secondary hover:bg-layer-1"
                >
                  丢弃
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
