import { createFileRoute } from "@tanstack/react-router";

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
  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[900px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Workspace and AI configuration.</p>
      </header>

      <Section title="Workspace">
        <Field label="Organization" value="Northwind Support" />
        <Field label="Plan" value="Enterprise" />
        <Field label="Region" value="eu-west-1" />
      </Section>

      <Section title="AI agents">
        <Toggle label="Triage Agent" defaultOn />
        <Toggle label="Knowledge Agent (RAG)" defaultOn />
        <Toggle label="Decision Agent" defaultOn />
        <Toggle label="Action Agent" defaultOn />
      </Section>

      <Section title="Notifications">
        <Toggle label="Email digest" defaultOn />
        <Toggle label="Slack alerts for urgent" defaultOn />
        <Toggle label="SMS on incidents" />
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

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-5 py-3 text-sm">
      <div className="text-muted-foreground">{label}</div>
      <div>{value}</div>
    </div>
  );
}

function Toggle({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  return (
    <label className="flex items-center justify-between px-5 py-3 text-sm cursor-pointer">
      <span>{label}</span>
      <span className="relative inline-block">
        <input type="checkbox" defaultChecked={defaultOn} className="peer sr-only" />
        <span className="block h-5 w-9 rounded-full bg-muted transition-colors peer-checked:bg-primary" />
        <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background transition-transform peer-checked:translate-x-4" />
      </span>
    </label>
  );
}
