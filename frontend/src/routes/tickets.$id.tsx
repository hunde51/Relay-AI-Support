import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, ArrowUpRight, Sparkles, Send, Clock, MessageSquare } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, api, type ApiTicket, type ApiMessage, type ApiEvent } from "@/lib/api/client";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";
import { AIActivityPanel } from "@/components/ai-panel/AIActivityPanel";
import { useAIStream } from "@/hooks/useAIStream";
import { cn } from "@/lib/utils";

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
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
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

type SuggestedAction = {
  id: string; action_type: string; payload: Record<string, unknown> | null;
  risk_level: string; requires_approval: boolean; approval_status: string; created_at: string;
};

function TicketDetail() {
  const initial = Route.useLoaderData() as ApiTicket;
  const [ticket, setTicket] = useState(initial);
  const [tab, setTab] = useState<"messages" | "timeline">("messages");
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [timeline, setTimeline] = useState<ApiEvent[]>([]);
  const [actions, setActions] = useState<SuggestedAction[]>([]);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const { steps, connected } = useAIStream(activeTicketId);

  const loadMessages = () => api.tickets.messages(ticket.id).then(setMessages).catch(() => null);
  const loadTimeline = () => api.tickets.timeline(ticket.id).then(setTimeline).catch(() => null);
  const loadActions = () =>
    api.ai.suggestedActions(ticket.id).then((a) => setActions(a as SuggestedAction[])).catch(() => null);

  useEffect(() => {
    loadMessages();
    loadTimeline();
    loadActions();
  }, [ticket.id]);

  const sendReply = async () => {
    if (!reply.trim()) return;
    setSending(true);
    const msg = await api.tickets.addMessage(ticket.id, { body: reply, sender_type: "agent" }).catch(() => null);
    if (msg) { setMessages((prev) => [...prev, msg]); setReply(""); }
    setSending(false);
  };

  const resolve = async () => {
    const updated = await api.tickets.resolve(ticket.id).catch(() => null);
    if (updated) { setTicket(updated); loadTimeline(); }
  };

  const escalate = async () => {
    const updated = await api.tickets.escalate(ticket.id).catch(() => null);
    if (updated) { setTicket(updated); loadTimeline(); }
  };

  const runAgent = async () => {
    setProcessing(true);
    setActiveTicketId(ticket.id);
    await api.ai.run(ticket.id).catch(() => null);
    setProcessing(false);
    loadActions();
  };

  const approveAction = async (id: string) => {
    await api.ai.approve(id).catch(() => null);
    loadActions();
  };

  const rejectAction = async (id: string) => {
    await api.ai.reject(id).catch(() => null);
    loadActions();
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-[1600px] mx-auto">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to tickets
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        {/* Main panel */}
        <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }} className="rounded-xl border border-border bg-card overflow-hidden">
          {/* Header */}
          <div className="border-b border-border p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">{ticket.id}</span>
              <span>·</span>
              <CategoryBadge category={ticket.category} />
              <PriorityBadge priority={ticket.priority} />
              <span className="ml-auto"><StatusBadge status={ticket.status} /></span>
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">{ticket.title}</h1>
            <div className="mt-1 text-sm text-muted-foreground">{ticket.message}</div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-border">
            {(["messages", "timeline"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={cn("flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium capitalize transition-colors",
                  tab === t ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground")}>
                {t === "messages" ? <MessageSquare className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                {t}
              </button>
            ))}
          </div>

          {/* Messages */}
          {tab === "messages" && (
            <div className="flex flex-col">
              <div className="flex-1 divide-y divide-border max-h-96 overflow-y-auto">
                {messages.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">No messages yet.</p>
                ) : messages.map((m) => (
                  <div key={m.id} className={cn("px-5 py-3", m.is_internal && "bg-warning/5")}>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                      <span className="capitalize font-medium text-foreground">{m.sender_type}</span>
                      {m.is_internal && <span className="rounded bg-warning/20 text-warning px-1">internal</span>}
                      <span className="ml-auto">{new Date(m.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm leading-relaxed">{m.body}</p>
                  </div>
                ))}
              </div>
              <div className="border-t border-border p-3 flex items-center gap-2">
                <input value={reply} onChange={(e) => setReply(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendReply()}
                  placeholder="Reply to customer…"
                  className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary/40" />
                <button onClick={sendReply} disabled={sending || !reply.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
                  <Send className="h-3.5 w-3.5" /> Send
                </button>
              </div>
            </div>
          )}

          {/* Timeline */}
          {tab === "timeline" && (
            <div className="divide-y divide-border max-h-[500px] overflow-y-auto">
              {timeline.length === 0 ? (
                <p className="px-5 py-8 text-center text-sm text-muted-foreground">No events yet.</p>
              ) : timeline.map((e) => (
                <div key={e.id} className="px-5 py-3 flex items-start gap-3 text-sm">
                  <div className="h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0" />
                  <div className="min-w-0">
                    <span className="font-medium capitalize">{e.event_type.replace(/_/g, " ")}</span>
                    {e.old_value && e.new_value && (
                      <span className="text-muted-foreground"> · {e.old_value} → {e.new_value}</span>
                    )}
                    <div className="text-xs text-muted-foreground">{new Date(e.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Sidebar */}
        <motion.aside initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }} className="space-y-4">
          {/* Actions */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="h-3.5 w-3.5" /> Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={runAgent} disabled={processing}
                className="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary/10 border border-primary/30 text-primary px-3 py-2 text-xs font-medium hover:bg-primary/20 disabled:opacity-50">
                <Sparkles className="h-3.5 w-3.5" />
                {processing ? "AI thinking…" : "Run AI Agent"}
              </button>
              <button onClick={resolve} disabled={ticket.status === "resolved" || ticket.status === "closed"}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-success/15 text-success border border-success/30 px-3 py-2 text-xs font-medium hover:bg-success/20 disabled:opacity-40">
                <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
              </button>
              <button onClick={escalate}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-warning/15 text-warning border border-warning/30 px-3 py-2 text-xs font-medium hover:bg-warning/20">
                <ArrowUpRight className="h-3.5 w-3.5" /> Escalate
              </button>
            </div>
          </div>

          {/* Suggested actions */}
          {actions.filter((a) => a.approval_status === "pending").length > 0 && (
            <div className="rounded-xl border border-warning/30 bg-warning/5 p-4 space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-warning">AI Suggestions</div>
              {actions.filter((a) => a.approval_status === "pending").map((a) => (
                <div key={a.id} className="rounded-lg border border-border bg-card p-3 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium capitalize">{a.action_type.replace(/_/g, " ")}</span>
                    <span className={cn("rounded px-1.5 py-0.5 text-[10px]",
                      a.risk_level === "high" ? "bg-destructive/15 text-destructive" :
                      a.risk_level === "medium" ? "bg-warning/15 text-warning" : "bg-success/15 text-success")}>
                      {a.risk_level}
                    </span>
                  </div>
                  {a.payload?.response != null && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{String(a.payload.response)}</p>
                  )}
                  <div className="flex gap-2">
                    <button onClick={() => approveAction(a.id)}
                      className="flex-1 rounded-md bg-success/15 text-success border border-success/30 py-1 text-xs font-medium hover:bg-success/25">
                      Approve
                    </button>
                    <button onClick={() => rejectAction(a.id)}
                      className="flex-1 rounded-md bg-destructive/10 text-destructive border border-destructive/20 py-1 text-xs font-medium hover:bg-destructive/20">
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* AI stream */}
          <AIActivityPanel liveSteps={activeTicketId ? steps : undefined} connected={connected} />

          {/* Metadata */}
          <div className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Metadata</div>
            <Row k="Created" v={new Date(ticket.created_at).toLocaleString()} />
            <Row k="Updated" v={new Date(ticket.updated_at).toLocaleString()} />
            <Row k="Status" v={ticket.status} />
            <Row k="Priority" v={ticket.priority} />
            <Row k="Category" v={ticket.category} />
            {ticket.resolved_at && <Row k="Resolved" v={new Date(ticket.resolved_at).toLocaleString()} />}
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
