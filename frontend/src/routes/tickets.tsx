import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { TicketsFeed } from "@/components/dashboard/TicketsFeed";
import { api, type ApiTicket } from "@/lib/api/client";
import { Filter, Plus } from "lucide-react";
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
  const [tickets, setTickets] = useState<ApiTicket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.tickets.list().then((data) => {
      setTickets(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const filtered = filter === "all" ? tickets : tickets.filter((t) => t.status === filter);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tickets</h1>
          <p className="text-sm text-muted-foreground">Manage and triage incoming support requests.</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-transform active:scale-95">
          <Plus className="h-4 w-4" />
          New ticket
        </button>
      </header>

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

      <TicketsFeed tickets={filtered} />
    </div>
  );
}
