import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, ArrowUpRight, Sparkles, Send } from "lucide-react";
import { useState } from "react";
import { ApiError, api, type ApiTicket } from "@/lib/api/client";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";
import { AIActivityPanel } from "@/components/ai-panel/AIActivityPanel";
import { useAIStream } from "@/hooks/useAIStream";

export const Route = createFileRoute("/tickets/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `${params.id} — Ticket` },
      { name: "description", content: `Ticket detail for ${params.id}` },
    ],
  }),
  loader: async ({ params }) => {
    try {
      return await api.tickets.get(params.id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        throw notFound();
      }
      throw error;
    }
  },
  notFoundComponent: () => (
    <div className="px-8 py-16 text-center">
      <p className="text-sm text-muted-foreground">Ticket not found.</p>
      <Link to="/tickets" className="text-sm text-primary">
        Back to tickets
      </Link>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="px-8 py-16 text-center text-sm text-destructive">{error.message}</div>
  ),
  component: TicketDetail,
});

function TicketDetail() {
  const t = Route.useLoaderData() as ApiTicket;
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const { steps, connected } = useAIStream(activeTicketId);

  const runAgent = async () => {
    setProcessing(true);
    setActiveTicketId(t.id); // opens WebSocket
    await api.agent.process(t.id);
    setProcessing(false);
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-[1600px] mx-auto">
      <Link
        to="/tickets"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4"
      >
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
              <span className="ml-auto">
                <StatusBadge status={t.status} />
              </span>
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">{t.title}</h1>
            <div className="mt-1 text-sm text-muted-foreground">{t.message}</div>
          </div>

          <div className="p-5">
            <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed border bg-muted/40 border-border">
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                Customer
              </div>
              {t.message}
            </div>
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
          {/* AI Action buttons */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="h-3.5 w-3.5" /> AI Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={runAgent}
                disabled={processing}
                className="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary/10 border border-primary/30 text-primary px-3 py-2 text-xs font-medium hover:bg-primary/20 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {processing ? "AI thinking…" : "Run AI Agent"}
              </button>
              <button className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-success/15 text-success border border-success/30 px-3 py-2 text-xs font-medium hover:bg-success/20">
                <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
              </button>
              <button className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-warning/15 text-warning border border-warning/30 px-3 py-2 text-xs font-medium hover:bg-warning/20">
                <ArrowUpRight className="h-3.5 w-3.5" /> Escalate
              </button>
            </div>
          </div>

          {/* Live AI reasoning panel */}
          <AIActivityPanel liveSteps={activeTicketId ? steps : undefined} connected={connected} />

          {/* Metadata */}
          <div className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Metadata
            </div>
            <Row k="Created" v={new Date(t.created_at).toLocaleString()} />
            <Row k="Status" v={t.status} />
            <Row k="Priority" v={t.priority} />
            <Row k="Category" v={t.category} />
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
