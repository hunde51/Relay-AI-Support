import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, ArrowUpRight, Sparkles, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { getTicket, type Ticket } from "@/data/mockTickets";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";

export const Route = createFileRoute("/tickets/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `${params.id} — Ticket` },
      { name: "description", content: `Ticket detail for ${params.id}` },
    ],
  }),
  loader: ({ params }) => {
    const t = getTicket(params.id);
    if (!t) throw notFound();
    return t;
  },
  notFoundComponent: () => (
    <div className="px-8 py-16 text-center">
      <p className="text-sm text-muted-foreground">Ticket not found.</p>
      <Link to="/tickets" className="text-sm text-primary">Back to tickets</Link>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="px-8 py-16 text-center text-sm text-destructive">{error.message}</div>
  ),
  component: TicketDetail,
});

function TicketDetail() {
  const t = Route.useLoaderData() as Ticket;
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const x = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(x);
  }, []);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-[1600px] mx-auto">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to tickets
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="rounded-xl border border-border bg-card overflow-hidden"
        >
          <div className="border-b border-border p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">{t.id}</span>
              <span>·</span>
              <CategoryBadge category={t.category} />
              <PriorityBadge priority={t.priority} />
              <span className="ml-auto"><StatusBadge status={t.status} /></span>
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">{t.subject}</h1>
            <div className="mt-1 text-sm text-muted-foreground">
              {t.customer} · <span className="text-foreground/70">{t.email}</span>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {loading ? (
              <>
                <div className="h-16 rounded-lg shimmer" />
                <div className="h-16 rounded-lg shimmer w-3/4 ml-auto" />
              </>
            ) : (
              t.messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.08 }}
                  className={`flex ${m.from === "customer" ? "justify-start" : "justify-end"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed border ${
                      m.from === "customer"
                        ? "bg-muted/40 border-border"
                        : m.from === "ai"
                          ? "bg-primary/10 border-primary/30 text-foreground"
                          : "bg-info/10 border-info/30"
                    }`}
                  >
                    <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                      {m.from === "customer" ? t.customer : m.from === "ai" ? "AI Agent" : "Support agent"}
                    </div>
                    {m.body}
                  </div>
                </motion.div>
              ))
            )}
          </div>

          <div className="border-t border-border p-3 flex items-center gap-2">
            <input
              placeholder="Reply to customer…"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary/40"
            />
            <button className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground active:scale-95 transition-transform">
              <Send className="h-3.5 w-3.5" /> Send
            </button>
          </div>
        </motion.div>

        <motion.aside
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-4"
        >
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="h-3.5 w-3.5" /> AI Analysis
            </div>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Customer reports a duplicate charge for the May invoice. Stripe confirms two identical charges within 12 seconds, consistent with a client-side retry. Policy permits auto-refund without manager approval.
            </p>

            <div className="mt-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-mono">92%</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "92%" }}
                  transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                  className="h-full rounded-full bg-gradient-to-r from-primary to-info"
                />
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-border bg-background/60 p-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Suggested reply</div>
              <p className="text-sm leading-relaxed">
                Hi {t.customer.split(" ")[0]}, thanks for the heads-up. We've confirmed a duplicate charge on your May invoice and issued a full refund for the duplicate. You'll see it on your statement within 5–10 business days. Sorry for the inconvenience!
              </p>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-success/15 text-success border border-success/30 px-3 py-2 text-xs font-medium transition-colors hover:bg-success/20">
                <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
              </button>
              <button className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-warning/15 text-warning border border-warning/30 px-3 py-2 text-xs font-medium transition-colors hover:bg-warning/20">
                <ArrowUpRight className="h-3.5 w-3.5" /> Escalate
              </button>
              <button
                disabled
                className="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground cursor-not-allowed"
              >
                <Sparkles className="h-3.5 w-3.5" /> Ask AI (coming soon)
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Metadata</div>
            <Row k="Created" v={new Date(t.createdAt).toLocaleString()} />
            <Row k="Updated" v={new Date(t.updatedAt).toLocaleString()} />
            {t.assignee && <Row k="Assignee" v={t.assignee} />}
            <Row k="Channel" v="Email" />
          </div>
        </motion.aside>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-mono text-right truncate">{v}</span>
    </div>
  );
}
