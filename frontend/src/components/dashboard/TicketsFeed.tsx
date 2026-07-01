import { motion, AnimatePresence } from "framer-motion";
import { Link } from "@tanstack/react-router";
import { CheckCircle2, ArrowUpRight, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import type { ApiTicket, TicketStatus } from "@/lib/api/client";
import { api } from "@/lib/api/client";
import { CategoryBadge, PriorityBadge, StatusBadge } from "@/components/tickets/Badges";

function relTime(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

export function TicketsFeed({ tickets, loading, onUpdate }: { tickets: ApiTicket[]; loading?: boolean; onUpdate?: () => void }) {
  const [rows, setRows] = useState<ApiTicket[]>(tickets);

  useEffect(() => {
    setRows(tickets);
  }, [tickets]);

  const advance = async (id: string) => {
    const ticket = rows.find((t) => t.id === id);
    if (!ticket) return;
    const next: TicketStatus =
      ticket.status === "open"
        ? "in_progress"
        : ticket.status === "in_progress"
          ? "resolved"
          : "resolved";
    const updated = await api.tickets.update(id, { status: next });
    setRows((prev) => prev.map((t) => (t.id === id ? updated : t)));
    onUpdate?.();
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
      {/* Desktop header row */}
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
              className="group md:grid md:grid-cols-[120px_1fr_120px_100px_140px_100px_80px] md:gap-4 md:px-4 md:py-3 px-3 py-3 text-sm transition-colors hover:bg-accent/40"
            >
              {/* Mobile card view */}
              <div className="md:hidden space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-xs text-muted-foreground shrink-0">{t.id}</span>
                    <StatusBadge status={t.status} />
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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
                  </div>
                </div>
                <div className="font-medium truncate">{t.title}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <CategoryBadge category={t.category} />
                  <PriorityBadge priority={t.priority} />
                  <span className="text-xs text-muted-foreground ml-auto">{relTime(t.created_at)}</span>
                </div>
              </div>

              {/* Desktop row */}
              <div className="hidden md:block font-mono text-xs text-muted-foreground self-center">{t.id}</div>
              <div className="hidden md:block min-w-0 self-center">
                <div className="truncate font-medium">{t.title}</div>
                <div className="truncate text-xs text-muted-foreground">{t.category}</div>
              </div>
              <div className="hidden md:block self-center">
                <CategoryBadge category={t.category} />
              </div>
              <div className="hidden md:block self-center">
                <PriorityBadge priority={t.priority} />
              </div>
              <div className="hidden md:block self-center">
                <StatusBadge status={t.status} />
              </div>
              <div className="hidden md:block self-center text-xs text-muted-foreground">
                {relTime(t.created_at)}
              </div>
              <div className="hidden md:flex self-center items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
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
