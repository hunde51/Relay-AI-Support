import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, type WorkspaceSettings, type AISettings, type NotificationSettings } from "@/lib/api/client";

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
  const [ws, setWs] = useState<WorkspaceSettings | null>(null);
  const [ai, setAi] = useState<AISettings | null>(null);
  const [notif, setNotif] = useState<NotificationSettings | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    api.settings.workspace().then(setWs).catch(() => null);
    api.settings.ai().then(setAi).catch(() => null);
    api.settings.notifications().then(setNotif).catch(() => null);
  }, []);

  const patchWs = async (field: keyof WorkspaceSettings, value: string) => {
    setSaving(field);
    const updated = await api.settings.patchWorkspace({ [field]: value }).catch(() => null);
    if (updated) setWs(updated);
    setSaving(null);
  };

  const patchAi = async (field: keyof AISettings, value: boolean | string) => {
    setSaving(field);
    const updated = await api.settings.patchAI({ [field]: value }).catch(() => null);
    if (updated) setAi(updated);
    setSaving(null);
  };

  const patchNotif = async (field: keyof NotificationSettings, value: boolean) => {
    setSaving(field);
    const updated = await api.settings.patchNotifications({ [field]: value }).catch(() => null);
    if (updated) setNotif(updated);
    setSaving(null);
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[900px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Workspace and AI configuration.</p>
      </header>

      <Section title="Workspace">
        {ws ? (
          <>
            <EditableField label="Organization" value={ws.name} saving={saving === "name"}
              onSave={(v) => patchWs("name", v)} />
            <EditableField label="Plan" value={ws.plan} saving={saving === "plan"}
              onSave={(v) => patchWs("plan", v)} />
            <EditableField label="Region" value={ws.region} saving={saving === "region"}
              onSave={(v) => patchWs("region", v)} />
          </>
        ) : (
          <SkeletonRows n={3} />
        )}
      </Section>

      <Section title="AI agents">
        {ai ? (
          <>
            <Toggle label="AI enabled" checked={ai.ai_enabled} saving={saving === "ai_enabled"}
              onChange={(v) => patchAi("ai_enabled", v)} />
            <Toggle label="Auto-resolve" checked={ai.auto_resolve_enabled} saving={saving === "auto_resolve_enabled"}
              onChange={(v) => patchAi("auto_resolve_enabled", v)} />
            <EditableField label="Human approval threshold" value={ai.human_approval_threshold}
              saving={saving === "human_approval_threshold"}
              onSave={(v) => patchAi("human_approval_threshold", v)} />
          </>
        ) : (
          <SkeletonRows n={3} />
        )}
      </Section>

      <Section title="Notifications">
        {notif ? (
          <>
            <Toggle label="Email digest" checked={notif.email_digest_enabled} saving={saving === "email_digest_enabled"}
              onChange={(v) => patchNotif("email_digest_enabled", v)} />
            <Toggle label="Slack alerts" checked={notif.slack_alerts_enabled} saving={saving === "slack_alerts_enabled"}
              onChange={(v) => patchNotif("slack_alerts_enabled", v)} />
            <Toggle label="SMS on incidents" checked={notif.sms_incidents_enabled} saving={saving === "sms_incidents_enabled"}
              onChange={(v) => patchNotif("sms_incidents_enabled", v)} />
          </>
        ) : (
          <SkeletonRows n={3} />
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
          className="font-mono text-right hover:text-primary transition-colors truncate max-w-[200px]"
          title="Click to edit">
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
