import { createFileRoute } from "@tanstack/react-router";
import { Ticket, Inbox, CheckCircle2, Timer } from "lucide-react";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { TicketsFeed } from "@/components/dashboard/TicketsFeed";
import { AIActivityPanel } from "@/components/ai-panel/AIActivityPanel";
import { useTickets } from "@/hooks/useTickets";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — AI SupportOps Hub" },
      { name: "description", content: "Live ticket feed, KPIs, and AI activity for your support operations." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { tickets, loading, error, refetch } = useTickets();

  if (error) return (
    <div className="flex flex-col items-center justify-center py-32 gap-3">
      <p className="text-sm text-destructive">{error}</p>
      <button onClick={refetch} className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-accent">Retry</button>
    </div>
  );

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Support overview</h1>
        <p className="text-sm text-muted-foreground">Real-time view of your queue and AI pipeline.</p>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard index={0} label="Total tickets" value={tickets.length} delta="+8.2%" trend="up" loading={loading} icon={<Ticket className="h-4 w-4" />} />
        <KpiCard index={1} label="Open tickets" value={tickets.filter(t => t.status === "open").length} delta="-3.1%" trend="down" loading={loading} icon={<Inbox className="h-4 w-4" />} />
        <KpiCard index={2} label="Resolved today" value={tickets.filter(t => t.status === "resolved").length} delta="+12%" trend="up" loading={loading} icon={<CheckCircle2 className="h-4 w-4" />} />
        <KpiCard index={3} label="Avg response" value="—" delta="" trend="up" loading={loading} icon={<Timer className="h-4 w-4" />} />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-3 min-w-0">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Live ticket feed</h2>
            <div className="text-xs text-muted-foreground">{tickets.length} tickets</div>
          </div>
          <TicketsFeed tickets={tickets} loading={loading} />
        </div>
        <aside className="min-w-0">
          <AIActivityPanel />
        </aside>
      </section>
    </div>
  );
}
