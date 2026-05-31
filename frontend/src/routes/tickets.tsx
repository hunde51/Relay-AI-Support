import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { TicketsFeed } from "@/components/dashboard/TicketsFeed";
import { useTickets } from "@/hooks/useTickets";
import { Filter, Plus, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/tickets")({
  head: () => ({
    meta: [
      { title: "Tickets — AI SupportOps Hub" },
      { name: "description", content: "All support tickets across your workspaces." },
    ],
  }),
  component: TicketsPage,
});

const statuses = ["all", "open", "in_progress", "resolved"] as const;
type Filter = (typeof statuses)[number];

function TicketsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const { tickets, loading, error, refetch } = useTickets();
  const filtered = filter === "all" ? tickets : tickets.filter((t) => t.status === filter);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tickets</h1>
          <p className="text-sm text-muted-foreground">Manage and triage incoming support requests.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={refetch} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-accent" title="Refresh">
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-transform active:scale-95">
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
            onClick={() => setFilter(s)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs capitalize transition-colors",
              filter === s
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-card text-muted-foreground hover:text-foreground",
            )}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      {!loading && filtered.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-muted-foreground">
          <p className="text-sm">No tickets found.</p>
          {filter !== "all" && (
            <button onClick={() => setFilter("all")} className="text-xs text-primary underline">
              Clear filter
            </button>
          )}
        </div>
      )}

      <TicketsFeed tickets={filtered} loading={loading} />
    </div>
  );
}
