import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, ArrowUpRight, Sparkles, Send, Clock, MessageSquare } from "lucide-react";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, api, type ApiTicket } from "@/lib/api/client";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";
import { AIActivityPanel } from "@/components/ai-panel/AIActivityPanel";
import { useAIStream } from "@/hooks/useAIStream";
import { cn } from "@/lib/utils";
import {
  keys,
  useTicketMessages, useTicketTimeline, useTicketActions,
  useResolveTicket, useEscalateTicket, useSendMessage, useRunAI,
  useApproveAction, useRejectAction, useExecuteAction,
} from "@/lib/queries";

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
  risk_level: string; requires_approval: boolean; approval_status: string;
};

function TicketDetail() {
  const qc = useQueryClient();
  const initial = Route.useLoaderData() as ApiTicket;
  // Keep ticket state in query cache so resolve/escalate updates propagate
  const ticket: ApiTicket = qc.getQueryData(keys.ticket(initial.id)) ?? initial;

  const [tab, setTab] = useState<"messages" | "timeline">("messages");
  const [reply, setReply] = useState("");
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const { steps, connected } = useAIStream(activeTicketId);

  const { data: messages = [] } = useTicketMessages(ticket.id);
  const { data: timeline = [] } = useTicketTimeline(ticket.id);
  const { data: rawActions = [] } = useTicketActions(ticket.id);
  const actions = rawActions as SuggestedAction[];

  const resolve = useResolveTicket(ticket.id);
  const escalate = useEscalateTicket(ticket.id);
  const sendMsg = useSendMessage(ticket.id);
  const runAI = useRunAI(ticket.id);
  const approve = useApproveAction(ticket.id);
  const reject = useRejectAction(ticket.id);
  const execute = useExecuteAction(ticket.id);
  const { data: audits = [] } = useTicketAudits(ticket.id);

  const currentTicket: ApiTicket = qc.getQueryData(keys.ticket(ticket.id)) ?? ticket;

  const sendReply = () => {
    if (!reply.trim()) return;
    sendMsg.mutate(reply, { onSuccess: () => setReply("") });
  };

  const handleRunAI = () => {
    setActiveTicketId(ticket.id);
    runAI.mutate();
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 max-w-[1600px] mx-auto">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to tickets
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }} className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="border-b border-border p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">{currentTicket.id}</span>
              <span>·</span>
              <CategoryBadge category={currentTicket.category} />
              <PriorityBadge priority={currentTicket.priority} />
              <span className="ml-auto"><StatusBadge status={currentTicket.status} /></span>
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">{currentTicket.title}</h1>
            <div className="mt-1 text-sm text-muted-foreground">{currentTicket.message}</div>
          </div>

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
                <button onClick={sendReply} disabled={sendMsg.isPending || !reply.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
                  <Send className="h-3.5 w-3.5" /> Send
                </button>
              </div>
            </div>
          )}

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

        <motion.aside initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }} className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="h-3.5 w-3.5" /> Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={handleRunAI} disabled={runAI.isPending}
                className="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary/10 border border-primary/30 text-primary px-3 py-2 text-xs font-medium hover:bg-primary/20 disabled:opacity-50">
                <Sparkles className="h-3.5 w-3.5" />
                {runAI.isPending ? "AI thinking…" : "Run AI Agent"}
              </button>
              <button onClick={() => resolve.mutate()}
                disabled={resolve.isPending || currentTicket.status === "resolved" || currentTicket.status === "closed"}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-success/15 text-success border border-success/30 px-3 py-2 text-xs font-medium hover:bg-success/20 disabled:opacity-40">
                <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
              </button>
              <button onClick={() => escalate.mutate()} disabled={escalate.isPending}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-warning/15 text-warning border border-warning/30 px-3 py-2 text-xs font-medium hover:bg-warning/20 disabled:opacity-40">
                <ArrowUpRight className="h-3.5 w-3.5" /> Escalate
              </button>
            </div>
          </div>

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
                    <button onClick={() => approve.mutate(a.id)} disabled={approve.isPending}
                      className="flex-1 rounded-md bg-success/15 text-success border border-success/30 py-1 text-xs font-medium hover:bg-success/25 disabled:opacity-50">
                      Approve
                    </button>
                    <button onClick={() => reject.mutate(a.id)} disabled={reject.isPending}
                      className="flex-1 rounded-md bg-destructive/10 text-destructive border border-destructive/20 py-1 text-xs font-medium hover:bg-destructive/20 disabled:opacity-50">
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <AIActivityPanel liveSteps={activeTicketId ? steps : undefined} connected={connected} />

          <div className="rounded-xl border border-border bg-card p-5 text-xs space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Metadata</div>
            <Row k="Created" v={new Date(currentTicket.created_at).toLocaleString()} />
            <Row k="Updated" v={new Date(currentTicket.updated_at).toLocaleString()} />
            <Row k="Status" v={currentTicket.status} />
            <Row k="Priority" v={currentTicket.priority} />
            <Row k="Category" v={currentTicket.category} />
            {currentTicket.resolved_at && <Row k="Resolved" v={new Date(currentTicket.resolved_at).toLocaleString()} />}
          </div>
        </motion.aside>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {

          {actions.filter((a) => a.approval_status === "approved").length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wider">Approved AI Actions</div>
              {actions.filter((a) => a.approval_status === "approved").map((a) => (
                <div key={a.id} className="rounded-lg border border-border bg-card p-3 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium capitalize">{a.action_type.replace(/_/g, " ")}</span>
                    <span className="text-xs text-muted-foreground">ready</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => execute.mutate(a.id)} disabled={execute.isPending}
                      className="flex-1 rounded-md bg-primary/15 text-primary border border-primary/30 py-1 text-xs font-medium hover:bg-primary/20 disabled:opacity-50">
                      Execute
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {audits.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wider">Audit Trail</div>
              {audits.map((a: any) => (
                <div key={a.id} className="text-xs text-muted-foreground">
                  <div className="flex items-center justify-between">
                    <div className="capitalize">{a.action.replace(/_/g, " ")}</div>
                    <div className="text-[10px]">{new Date(a.created_at).toLocaleString()}</div>
                  </div>
                  <div className="text-[11px]">By: {a.actor_user_id ?? a.actor_type}</div>
                </div>
              ))}
            </div>
          )}
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-mono text-right truncate">{v}</span>
    </div>
  );
}
