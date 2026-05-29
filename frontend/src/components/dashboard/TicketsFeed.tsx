import { motion, AnimatePresence } from "framer-motion";
import { Link } from "@tanstack/react-router";
import { CheckCircle2, ArrowUpRight, Eye } from "lucide-react";
import { useState } from "react";
import type { Ticket } from "@/data/mockTickets";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";

function relTime(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

export function TicketsFeed({ tickets, loading }: { tickets: Ticket[]; loading?: boolean }) {
  const [rows, setRows] = useState(tickets);

  const advance = (id: string) => {
    setRows((prev) =>
      prev.map((t) =>
        t.id === id
          ? { ...t, status: t.status === "open" ? "in_progress" : t.status === "in_progress" ? "resolved" : "resolved" }
          : t,
      ),
    );
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 rounded-lg shimmer" />
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="hidden md:grid grid-cols-[120px_1fr_120px_100px_140px_100px_80px] gap-4 border-b border-border bg-muted/30 px-4 py-2.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        <div>Ticket</div>
        <div>Customer & subject</div>
        <div>Category</div>
        <div>Priority</div>
        <div>Status</div>
        <div>Updated</div>
        <div />
      </div>
      <div className="divide-y divide-border">
        <AnimatePresence initial={false}>
          {rows.map((t, i) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.04, ease: "easeOut" }}
              className="group grid md:grid-cols-[120px_1fr_120px_100px_140px_100px_80px] grid-cols-2 gap-x-4 gap-y-2 px-4 py-3 text-sm transition-colors hover:bg-accent/40"
            >
              <div className="font-mono text-xs text-muted-foreground self-center">{t.id}</div>
              <div className="min-w-0 self-center">
                <div className="truncate font-medium">{t.subject}</div>
                <div className="truncate text-xs text-muted-foreground">{t.customer}</div>
              </div>
              <div className="self-center"><CategoryBadge category={t.category} /></div>
              <div className="self-center"><PriorityBadge priority={t.priority} /></div>
              <div className="self-center"><StatusBadge status={t.status} /></div>
              <div className="self-center text-xs text-muted-foreground">{relTime(t.updatedAt)}</div>
              <div className="self-center flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <Link
                  to="/tickets/$id"
                  params={{ id: t.id }}
                  className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="View"
                >
                  <Eye className="h-3.5 w-3.5" />
                </Link>
                <button
                  onClick={() => advance(t.id)}
                  className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-success"
                  title="Resolve"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                </button>
                <button
                  className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-warning"
                  title="Escalate"
                >
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
