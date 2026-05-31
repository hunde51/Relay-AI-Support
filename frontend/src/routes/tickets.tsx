import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { TicketsFeed } from "@/components/dashboard/TicketsFeed";
import { useTickets } from "@/hooks/useTickets";
import { Filter, Plus, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TicketStatus } from "@/lib/api/client";
import { CreateTicketModal } from "@/components/tickets/CreateTicketModal";

export const Route = createFileRoute("/tickets")({
  head: () => ({
    meta: [
      { title: "Tickets — AI SupportOps Hub" },
      { name: "description", content: "All support tickets across your workspaces." },
    ],
  }),
  component: TicketsPage,
});

const statuses = ["all", "open", "in_progress", "waiting_on_customer", "resolved", "closed"] as const;
type Filter = (typeof statuses)[number];

function TicketsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  const { tickets, total, pages, loading, error, refetch } = useTickets({
    status: filter === "all" ? undefined : (filter as TicketStatus),
    page,
    page_size: 25,
  });

  const handleFilterChange = (f: Filter) => {
    setFilter(f);
    setPage(1);
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tickets</h1>
          <p className="text-sm text-muted-foreground">Manage and triage incoming support requests.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refetch}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-accent"
            title="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-transform active:scale-95"
          >
            <Plus className="h-4 w-4" />
            New ticket
          </button>
        </div>
      </header>

      {error && (
        <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
          <button onClick={refetch} className="text-xs underline">Retry</button>
        </div>
      )}

      <div className="flex items-center gap-2 overflow-x-auto">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => handleFilterChange(s)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs capitalize transition-colors",
              filter === s
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:text-foreground",
            )}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">{total} total</span>
      </div>

      {!loading && tickets.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-muted-foreground">
          <p className="text-sm">No tickets found.</p>
          {filter !== "all" && (
            <button onClick={() => handleFilterChange("all")} className="text-xs text-primary underline">
              Clear filter
            </button>
          )}
        </div>
      )}

      <TicketsFeed tickets={tickets} loading={loading} onUpdate={refetch} />

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border disabled:opacity-40 hover:bg-accent"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-muted-foreground">
            Page {page} of {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border disabled:opacity-40 hover:bg-accent"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {showCreate && <CreateTicketModal onClose={() => setShowCreate(false)} onCreated={refetch} />}
    </div>
  );
}
