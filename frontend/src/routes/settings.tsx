import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  useWorkspaceSettings, useAISettings, useNotificationSettings,
  usePatchWorkspace, usePatchAISettings, usePatchNotifications,
} from "@/lib/queries";
import type { WorkspaceSettings, AISettings, NotificationSettings } from "@/lib/api/client";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — AI SupportOps Hub" },
      { name: "description", content: "Workspace, AI, and notification settings." },
    ],
  }),
  component: Settings,
});

function Settings() {
  const { data: ws, isLoading: wsLoading } = useWorkspaceSettings();
  const { data: ai, isLoading: aiLoading } = useAISettings();
  const { data: notif, isLoading: notifLoading } = useNotificationSettings();

  const patchWs = usePatchWorkspace();
  const patchAi = usePatchAISettings();
  const patchNotif = usePatchNotifications();

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[900px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Workspace and AI configuration.</p>
      </header>

      <Section title="Workspace">
        {wsLoading || !ws ? <SkeletonRows n={3} /> : (
          <>
            <EditableField label="Organization" value={ws.name} saving={patchWs.isPending}
              onSave={(v) => patchWs.mutate({ name: v })} />
            <EditableField label="Plan" value={ws.plan} saving={patchWs.isPending}
              onSave={(v) => patchWs.mutate({ plan: v })} />
            <EditableField label="Region" value={ws.region} saving={patchWs.isPending}
              onSave={(v) => patchWs.mutate({ region: v })} />
          </>
        )}
      </Section>

      <Section title="AI agents">
        {aiLoading || !ai ? <SkeletonRows n={3} /> : (
          <>
            <Toggle label="AI enabled" checked={ai.ai_enabled} saving={patchAi.isPending}
              onChange={(v) => patchAi.mutate({ ai_enabled: v })} />
            <Toggle label="Auto-resolve" checked={ai.auto_resolve_enabled} saving={patchAi.isPending}
              onChange={(v) => patchAi.mutate({ auto_resolve_enabled: v })} />
            <EditableField label="Approval threshold" value={ai.human_approval_threshold} saving={patchAi.isPending}
              onSave={(v) => patchAi.mutate({ human_approval_threshold: v })} />
          </>
        )}
      </Section>

      <Section title="Notifications">
        {notifLoading || !notif ? <SkeletonRows n={3} /> : (
          <>
            <Toggle label="Email digest" checked={notif.email_digest_enabled} saving={patchNotif.isPending}
              onChange={(v) => patchNotif.mutate({ email_digest_enabled: v })} />
            <Toggle label="Slack alerts" checked={notif.slack_alerts_enabled} saving={patchNotif.isPending}
              onChange={(v) => patchNotif.mutate({ slack_alerts_enabled: v })} />
            <Toggle label="SMS on incidents" checked={notif.sms_incidents_enabled} saving={patchNotif.isPending}
              onChange={(v) => patchNotif.mutate({ sms_incidents_enabled: v })} />
          </>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="border-b border-border px-5 py-3 text-sm font-semibold">{title}</div>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

function EditableField({ label, value, onSave, saving }: {
  label: string; value: string; onSave: (v: string) => void; saving?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const commit = () => { onSave(draft); setEditing(false); };

  return (
    <div className="flex items-center justify-between px-5 py-3 text-sm gap-4">
      <div className="text-muted-foreground shrink-0">{label}</div>
      {editing ? (
        <div className="flex items-center gap-2">
          <input value={draft} onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
            className="rounded border border-border bg-background px-2 py-1 text-sm outline-none focus:border-primary w-40" autoFocus />
          <button onClick={commit} className="text-xs text-primary hover:underline">Save</button>
          <button onClick={() => setEditing(false)} className="text-xs text-muted-foreground hover:underline">Cancel</button>
        </div>
      ) : (
        <button onClick={() => { setDraft(value); setEditing(true); }}
          className="font-mono text-right hover:text-primary transition-colors truncate max-w-[200px]" title="Click to edit">
          {saving ? <span className="text-muted-foreground">saving…</span> : value}
        </button>
      )}
    </div>
  );
}

function Toggle({ label, checked, onChange, saving }: {
  label: string; checked: boolean; onChange: (v: boolean) => void; saving?: boolean;
}) {
  return (
    <label className="flex items-center justify-between px-5 py-3 text-sm cursor-pointer">
      <span>{label}</span>
      <span className="relative inline-block">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
          disabled={saving} className="peer sr-only" />
        <span className="block h-5 w-9 rounded-full bg-muted transition-colors peer-checked:bg-primary peer-disabled:opacity-50" />
        <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background transition-transform peer-checked:translate-x-4" />
      </span>
    </label>
  );
}

function SkeletonRows({ n }: { n: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="flex items-center justify-between px-5 py-3 gap-4">
          <div className="h-4 w-24 rounded shimmer" />
          <div className="h-4 w-32 rounded shimmer" />
        </div>
      ))}
    </>
  );
}
