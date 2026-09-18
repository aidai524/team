/**
 * AI usage and workspace toggle (God Mode).
 *
 * Talks to the AI Gateway at /ai/* on the same origin; Caddy injects the
 * gateway key server-side, so the browser needs no credentials here.
 */

"use client";

import { useState } from "react";

type UsageData = {
  total_requests: number;
  avg_latency_ms: number;
  total_latency_ms: number;
};

export function InstanceAIUsage() {
  const [slug, setSlug] = useState("");
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!slug.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const [usageRes, settingRes] = await Promise.all([
        fetch(`/ai/usage?workspace_slug=${encodeURIComponent(slug.trim())}`),
        fetch(`/ai/settings/ai?workspace_slug=${encodeURIComponent(slug.trim())}`),
      ]);
      if (!usageRes.ok) throw new Error(`usage ${usageRes.status}`);
      setUsage(await usageRes.json());
      if (settingRes.ok) {
        const setting = await settingRes.json();
        setEnabled(setting.ai_enabled);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const toggle = async (value: boolean) => {
    if (!slug.trim()) return;
    const res = await fetch("/ai/settings/ai", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_slug: slug.trim(), ai_enabled: value }),
    });
    if (res.ok) setEnabled(value);
  };

  return (
    <div className="mt-8 space-y-4 border-t border-subtle pt-6">
      <div className="pb-1 text-18 font-medium text-primary">AI usage &amp; controls</div>
      <div className="text-13 font-regular text-tertiary">
        Query AI gateway usage and toggle AI per workspace. Requires a running AI gateway.
      </div>

      <div className="flex items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-13 text-secondary">Workspace slug</label>
          <input
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            placeholder="team"
            className="rounded-sm border border-subtle bg-surface-1 px-2 py-1.5 text-13 text-primary outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading || !slug.trim()}
          className="rounded-sm bg-accent-primary px-3 py-1.5 text-13 font-medium text-on-color disabled:opacity-50"
        >
          {loading ? "Loading…" : "Query"}
        </button>
      </div>

      {error && <div className="text-13 text-danger-primary">{error}</div>}

      {usage && (
        <div className="grid w-full max-w-2xl grid-cols-3 gap-4">
          <div className="rounded-sm border border-subtle bg-surface-1 p-3">
            <div className="text-13 text-tertiary">Total requests</div>
            <div className="text-18 font-medium text-primary">{usage.total_requests}</div>
          </div>
          <div className="rounded-sm border border-subtle bg-surface-1 p-3">
            <div className="text-13 text-tertiary">Avg latency</div>
            <div className="text-18 font-medium text-primary">{usage.avg_latency_ms} ms</div>
          </div>
          <div className="rounded-sm border border-subtle bg-surface-1 p-3">
            <div className="text-13 text-tertiary">Total latency</div>
            <div className="text-18 font-medium text-primary">{usage.total_latency_ms} ms</div>
          </div>
        </div>
      )}

      {enabled !== null && (
        <div className="flex items-center gap-3">
          <span className="text-13 text-secondary">AI enabled for this workspace:</span>
          <button
            type="button"
            onClick={() => void toggle(!enabled)}
            className={`rounded-sm px-3 py-1 text-13 font-medium ${
              enabled ? "bg-accent-subtle text-accent-secondary" : "bg-surface-2 text-tertiary"
            }`}
          >
            {enabled ? "Enabled" : "Disabled"}
          </button>
        </div>
      )}
    </div>
  );
}
