import { createFileRoute } from "@tanstack/react-router";
import { BookOpen, Search } from "lucide-react";

export const Route = createFileRoute("/knowledge-base")({
  head: () => ({
    meta: [
      { title: "Knowledge Base — AI SupportOps Hub" },
      { name: "description", content: "Articles and runbooks used by AI and human agents." },
    ],
  }),
  component: KB,
});

const articles = [
  { title: "Refund policy — duplicate charges", category: "Billing", views: 1240 },
  { title: "Stripe idempotency keys", category: "Engineering", views: 812 },
  { title: "Resetting 2FA for end users", category: "Account", views: 2104 },
  { title: "SSO with Okta — common errors", category: "Account", views: 614 },
  { title: "Webhook delivery troubleshooting", category: "Engineering", views: 933 },
  { title: "Inviting teammates to a workspace", category: "General", views: 3120 },
];

function KB() {
  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1200px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge base</h1>
        <p className="text-sm text-muted-foreground">Source of truth for AI retrieval and agent answers.</p>
      </header>

      <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground" placeholder="Search articles…" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {articles.map((a) => (
          <div key={a.title} className="group rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/30">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="font-medium truncate">{a.title}</div>
                <div className="text-xs text-muted-foreground">{a.category} · {a.views.toLocaleString()} views</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
