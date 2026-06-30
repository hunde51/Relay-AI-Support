import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Key, Webhook, Plus, Trash2, RefreshCw, Copy, Globe } from "lucide-react";
import {
  useWorkspaceSettings, useAISettings, useNotificationSettings,
  usePatchWorkspace, usePatchAISettings, usePatchNotifications,
  useApiKeys, useCreateApiKey, useRevokeApiKey, useRotateApiKey,
  useWebhookEndpoints, useCreateWebhookEndpoint, useDeleteWebhookEndpoint,
  useWebhookDeliveries, useTestWebhookEndpoint,
  useWidgetKeys, useCreateWidgetKey, useUpdateWidgetKey, useRevokeWidgetKey,
} from "@/lib/queries";
import type { WorkspaceSettings, AISettings, NotificationSettings, ApiKey, WebhookEndpoint, WebhookDelivery, WidgetKey } from "@/lib/api/client";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — AI SupportOps Hub" },
      { name: "description", content: "Workspace, AI, and notification settings." },
    ],
  }),
  component: Settings,
});

const AVAILABLE_EVENTS = ["ticket.created", "ticket.resolved", "ticket.escalated", "ai.action_suggested", "ai.action_executed"];

function Settings() {
  const { data: ws, isLoading: wsLoading } = useWorkspaceSettings();
  const { data: ai, isLoading: aiLoading } = useAISettings();
  const { data: notif, isLoading: notifLoading } = useNotificationSettings();
  const { data: apiKeys = [], isLoading: keysLoading } = useApiKeys();
  const { data: endpoints = [], isLoading: epsLoading } = useWebhookEndpoints();
  const { data: deliveries = [], isLoading: delLoading } = useWebhookDeliveries();

  const patchWs = usePatchWorkspace();
  const patchAi = usePatchAISettings();
  const patchNotif = usePatchNotifications();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();
  const rotateKey = useRotateApiKey();
  const createEp = useCreateWebhookEndpoint();
  const deleteEp = useDeleteWebhookEndpoint();
  const testEp = useTestWebhookEndpoint();

  const { data: widgetKeys = [], isLoading: widgetKeysLoading } = useWidgetKeys();
  const createWidgetKey = useCreateWidgetKey();
  const updateWidgetKey = useUpdateWidgetKey();
  const revokeWidgetKey = useRevokeWidgetKey();

  const [newKeyName, setNewKeyName] = useState("");
  const [newEpUrl, setNewEpUrl] = useState("");
  const [newEpEvents, setNewEpEvents] = useState<string[]>(["ticket.resolved"]);
  const [newWidgetName, setNewWidgetName] = useState("");
  const [newWidgetOrigins, setNewWidgetOrigins] = useState("");
  const [newWidgetKeyResult, setNewWidgetKeyResult] = useState<{ key: string; name: string } | null>(null);
  const [editingWidgetId, setEditingWidgetId] = useState<string | null>(null);
  const [editingWidgetOrigins, setEditingWidgetOrigins] = useState("");

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[900px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Workspace, AI, and notification settings.</p>
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

      <Section title="API Keys" icon={<Key className="h-4 w-4" />}>
        {keysLoading ? <SkeletonRows n={2} /> : (
          <>
            <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
              <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="New key name…"
                className="flex-1 rounded border border-border bg-background px-3 py-1.5 text-sm outline-none focus:border-primary"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newKeyName.trim()) {
                    createKey.mutate({ name: newKeyName.trim() });
                    setNewKeyName("");
                  }
                }}
              />
              <button onClick={() => { if (newKeyName.trim()) { createKey.mutate({ name: newKeyName.trim() }); setNewKeyName(""); } }}
                disabled={createKey.isPending || !newKeyName.trim()}
                className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-3 w-3" /> Create
              </button>
            </div>
            {apiKeys.length === 0 ? (
              <p className="px-5 py-4 text-xs text-muted-foreground">No API keys yet.</p>
            ) : apiKeys.map((k) => (
              <ApiKeyRow key={k.id} keyData={k} onRevoke={() => revokeKey.mutate(k.id)} onRotate={() => rotateKey.mutate(k.id)} />
            ))}
          </>
        )}
      </Section>

      <Section title="Support Widget" icon={<Globe className="h-4 w-4" />}>
        {widgetKeysLoading ? <SkeletonRows n={2} /> : (
          <>
            <div className="flex flex-col gap-2 px-5 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <input value={newWidgetName} onChange={(e) => setNewWidgetName(e.target.value)}
                  placeholder="Widget name…"
                  className="flex-1 rounded border border-border bg-background px-3 py-1.5 text-sm outline-none focus:border-primary"
                />
                <button onClick={() => {
                  if (newWidgetName.trim()) {
                    createWidgetKey.mutate({
                      name: newWidgetName.trim(),
                      allowed_origins: newWidgetOrigins.split("\n").map((s) => s.trim()).filter(Boolean),
                    }, {
                      onSuccess: (data) => {
                        setNewWidgetKeyResult({ key: (data as { key: string }).key, name: data.name });
                        setNewWidgetName("");
                        setNewWidgetOrigins("");
                      },
                    });
                  }
                }}
                  disabled={createWidgetKey.isPending || !newWidgetName.trim()}
                  className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50 shrink-0"
                >
                  <Plus className="h-3 w-3" /> Create
                </button>
              </div>
              <textarea value={newWidgetOrigins} onChange={(e) => setNewWidgetOrigins(e.target.value)}
                placeholder="Allowed origins (one per line, leave empty for all origins)"
                className="w-full rounded border border-border bg-background px-3 py-1.5 text-xs outline-none focus:border-primary resize-none"
                rows={2}
              />
            </div>

            {newWidgetKeyResult && (
              <div className="px-5 py-3 bg-primary/5 border-b border-border">
                <p className="text-xs font-semibold text-primary mb-1">Widget key created — copy it now, it won't be shown again!</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs font-mono bg-background rounded px-2 py-1 break-all">{newWidgetKeyResult.key}</code>
                  <button onClick={() => {
                    navigator.clipboard.writeText(newWidgetKeyResult.key).then(() => {
                      setNewWidgetKeyResult(null);
                    });
                  }} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent shrink-0">
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => setNewWidgetKeyResult(null)} className="text-xs text-muted-foreground hover:underline shrink-0">
                    Dismiss
                  </button>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  <p>Embed code:</p>
                  <code className="block bg-background rounded px-2 py-1 mt-1 font-mono text-xs break-all">
                    {`<script src="${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/widget.js" data-key="${newWidgetKeyResult.key}" data-color="#6366f1" data-title="Support"></script>`}
                  </code>
                </div>
              </div>
            )}

            {widgetKeys.length === 0 ? (
              <p className="px-5 py-4 text-xs text-muted-foreground">No widget keys yet.</p>
            ) : widgetKeys.map((k) => (
              <WidgetKeyRow key={k.id} keyData={k}
                onRevoke={() => revokeWidgetKey.mutate(k.id)}
                onUpdate={(data) => updateWidgetKey.mutate({ id: k.id, data })}
                editingWidgetId={editingWidgetId}
                setEditingWidgetId={setEditingWidgetId}
                editingWidgetOrigins={editingWidgetOrigins}
                setEditingWidgetOrigins={setEditingWidgetOrigins}
              />
            ))}
          </>
        )}
      </Section>

      <Section title="Webhooks" icon={<Webhook className="h-4 w-4" />}>
        {epsLoading ? <SkeletonRows n={2} /> : (
          <>
            <div className="flex flex-col gap-2 px-5 py-3 border-b border-border">
              <input value={newEpUrl} onChange={(e) => setNewEpUrl(e.target.value)}
                placeholder="https://example.com/webhooks/relayai"
                className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm outline-none focus:border-primary"
              />
              <div className="flex items-center gap-2 flex-wrap">
                {AVAILABLE_EVENTS.map((ev) => (
                  <label key={ev} className="flex items-center gap-1 text-xs cursor-pointer">
                    <input type="checkbox" checked={newEpEvents.includes(ev)}
                      onChange={() => setNewEpEvents((prev) => prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev])}
                      className="accent-primary"
                    />
                    {ev}
                  </label>
                ))}
              </div>
              <button onClick={() => {
                if (newEpUrl.trim() && newEpEvents.length > 0) {
                  createEp.mutate({ url: newEpUrl.trim(), events: newEpEvents });
                  setNewEpUrl("");
                }
              }}
                disabled={createEp.isPending || !newEpUrl.trim() || newEpEvents.length === 0}
                className="self-end inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-3 w-3" /> Add endpoint
              </button>
            </div>
            {endpoints.length === 0 ? (
              <p className="px-5 py-4 text-xs text-muted-foreground">No webhook endpoints configured.</p>
            ) : endpoints.map((ep) => (
              <WebhookRow key={ep.id} ep={ep} onDelete={() => deleteEp.mutate(ep.id)} onTest={() => testEp.mutate(ep.id)} />
            ))}
          </>
        )}
        {deliveries.length > 0 && (
          <div className="border-t border-border">
            <div className="px-5 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent deliveries</div>
            {deliveries.slice(0, 5).map((d) => (
              <DeliveryRow key={d.id} delivery={d} />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children, icon }: { title: string; children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="border-b border-border px-5 py-3 text-sm font-semibold flex items-center gap-2">
        {icon}
        {title}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

function ApiKeyRow({ keyData, onRevoke, onRotate }: { keyData: ApiKey; onRevoke: () => void; onRotate: () => void }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = (key: string) => {
    navigator.clipboard.writeText(key).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
  };
  return (
    <div className="px-5 py-3 text-sm flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="font-medium">{keyData.name}</div>
        <div className="text-xs text-muted-foreground font-mono">
          {keyData.key_prefix}…{keyData.is_active ? "active" : "revoked"}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button onClick={() => handleCopy(keyData.key_prefix)} title="Copy prefix"
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent">
          <Copy className="h-3.5 w-3.5" />
        </button>
        <button onClick={onRotate} title="Rotate key"
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
        <button onClick={onRevoke} title="Revoke key"
          className="rounded p-1 text-destructive/70 hover:text-destructive hover:bg-destructive/10">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function WebhookRow({ ep, onDelete, onTest }: { ep: WebhookEndpoint; onDelete: () => void; onTest: () => void }) {
  return (
    <div className="px-5 py-3 text-sm flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="truncate font-mono text-xs">{ep.url}</div>
        <div className="text-xs text-muted-foreground">
          {ep.events.length} event{ep.events.length !== 1 ? "s" : ""}
          {ep.is_active ? " · active" : " · inactive"}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button onClick={onTest} title="Send test"
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent text-xs">
          Test
        </button>
        <button onClick={onDelete} title="Delete endpoint"
          className="rounded p-1 text-destructive/70 hover:text-destructive hover:bg-destructive/10">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function DeliveryRow({ delivery }: { delivery: WebhookDelivery }) {
  const statusColor = delivery.status === "delivered" ? "text-success" :
    delivery.status === "failed" ? "text-destructive" : "text-muted-foreground";
  return (
    <div className="px-5 py-2 text-xs flex items-center justify-between gap-4">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${statusColor.replace("text-", "bg-")}`} />
        <span className="font-mono">{delivery.event_type}</span>
      </div>
      <div className="flex items-center gap-3 shrink-0 text-muted-foreground">
        <span className={statusColor}>{delivery.status}</span>
        <span>{delivery.attempts} attempt{delivery.attempts !== 1 ? "s" : ""}</span>
      </div>
    </div>
  );
}

function WidgetKeyRow({ keyData, onRevoke, onUpdate, editingWidgetId, setEditingWidgetId, editingWidgetOrigins, setEditingWidgetOrigins }: {
  keyData: WidgetKey;
  onRevoke: () => void;
  onUpdate: (data: { name?: string; allowed_origins?: string[] }) => void;
  editingWidgetId: string | null;
  setEditingWidgetId: (v: string | null) => void;
  editingWidgetOrigins: string;
  setEditingWidgetOrigins: (v: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const isEditing = editingWidgetId === keyData.id;

  return (
    <div className="px-5 py-3 text-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="font-medium">{keyData.name}</div>
          <div className="text-xs text-muted-foreground font-mono">
            {keyData.key_prefix}…{keyData.is_active ? "active" : "revoked"}
            {keyData.last_used_at ? ` · last used ${new Date(keyData.last_used_at).toLocaleDateString()}` : " · never used"}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={() => {
            setEditingWidgetId(isEditing ? null : keyData.id);
            setEditingWidgetOrigins((keyData.allowed_origins ?? []).join("\n"));
          }} title="Edit origins"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent">
            <Globe className="h-3.5 w-3.5" />
          </button>
          <button onClick={onRevoke} title="Revoke key"
            className="rounded p-1 text-destructive/70 hover:text-destructive hover:bg-destructive/10">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {isEditing && (
        <div className="mt-2 flex flex-col gap-2">
          <textarea value={editingWidgetOrigins} onChange={(e) => setEditingWidgetOrigins(e.target.value)}
            placeholder="Allowed origins (one per line)"
            className="w-full rounded border border-border bg-background px-2 py-1 text-xs outline-none focus:border-primary resize-none"
            rows={2}
          />
          <div className="flex items-center gap-2">
            <button onClick={() => {
              onUpdate({ allowed_origins: editingWidgetOrigins.split("\n").map((s) => s.trim()).filter(Boolean) });
              setEditingWidgetId(null);
            }} className="text-xs text-primary hover:underline">Save</button>
            <button onClick={() => setEditingWidgetId(null)} className="text-xs text-muted-foreground hover:underline">Cancel</button>
          </div>
        </div>
      )}
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
