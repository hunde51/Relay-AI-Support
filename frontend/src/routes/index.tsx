import { createFileRoute, Link } from "@tanstack/react-router";
import { Ticket, Inbox, CheckCircle2, Timer, Activity, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { TicketsFeed } from "@/components/dashboard/TicketsFeed";
import { AIActivityPanel } from "@/components/ai-panel/AIActivityPanel";
import { useTickets } from "@/hooks/useTickets";
import { useWSSubscription } from "@/hooks/useWSSubscription";
import { useDashboardSummary, useRecentActivity, useTicketVolume, useUsageSummary } from "@/lib/queries";
import type { RecentActivity } from "@/lib/api/client";

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
  useWSSubscription("/ws/tickets");
  const { tickets, total, loading, error, refetch } = useTickets({ page_size: 25 });
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: usage } = useUsageSummary();
  const { data: activity = [] } = useRecentActivity();
  const { data: volumeData = [] } = useTicketVolume();
  const volumeItems = volumeData.map((r: { day: string; count: number }) => ({ day: r.day.slice(5), count: r.count }));

  if (error)
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-3">
        <p className="text-sm text-destructive">{error}</p>
        <button onClick={refetch} className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-accent">
          Retry
        </button>
      </div>
    );

  const avgResponse = summary?.avg_first_response_minutes != null
    ? `${summary.avg_first_response_minutes}m`
    : "—";

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Support overview</h1>
        <p className="text-sm text-muted-foreground">Real-time view of your queue and AI pipeline.</p>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard index={0} label="Total tickets" value={summary?.total_tickets ?? total} delta="" trend="up" loading={summaryLoading} icon={<Ticket className="h-4 w-4" />} />
        <KpiCard index={1} label="Open tickets" value={summary?.open_tickets ?? 0} delta="" trend="down" loading={summaryLoading} icon={<Inbox className="h-4 w-4" />} />
        <KpiCard index={2} label="Resolved today" value={summary?.resolved_today ?? 0} delta="" trend="up" loading={summaryLoading} icon={<CheckCircle2 className="h-4 w-4" />} />
        <KpiCard index={3} label="Avg response" value={avgResponse} delta="" trend="up" loading={summaryLoading} icon={<Timer className="h-4 w-4" />} />
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard index={4} label="AI runs (month)" value={usage?.ai_runs_executed ?? 0} delta="" trend="up" loading={!usage} icon={<Activity className="h-4 w-4" />} />
        <KpiCard index={5} label="API requests (month)" value={usage?.api_requests ?? 0} delta="" trend="up" loading={!usage} icon={<TrendingUp className="h-4 w-4" />} />
        <KpiCard index={6} label="AI cost (month)" value={usage ? `$${usage.llm_cost_usd.toFixed(2)}` : "—"} delta="" trend="up" loading={!usage} icon={<Activity className="h-4 w-4" />} />
        <KpiCard index={7} label="Knowledge chunks" value={usage?.knowledge_chunks ?? 0} delta="" trend="up" loading={!usage} icon={<Activity className="h-4 w-4" />} />
      </section>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }} className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm font-semibold">Ticket volume (last 14 days)</div>
        </div>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={volumeItems} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="g-volume" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--muted-foreground)" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Area type="monotone" dataKey="count" stroke="var(--chart-1)" strokeWidth={2} fill="url(#g-volume)" />
          </AreaChart>
        </ResponsiveContainer>
      </motion.div>

      <section className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-3 min-w-0">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Live ticket feed</h2>
            <div className="text-xs text-muted-foreground">{summary?.total_tickets ?? total} tickets</div>
          </div>
          <TicketsFeed tickets={tickets} loading={loading} onUpdate={refetch} />
        </div>
        <aside className="min-w-0 space-y-4">
          <AIActivityPanel />
          <RecentActivityFeed items={activity} loading={false} />
        </aside>
      </section>
    </div>
  );
}

function RecentActivityFeed({ items, loading }: { items: RecentActivity[]; loading: boolean }) {
  if (loading) return <div className="h-40 rounded-xl shimmer" />;
  if (items.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Activity className="h-3.5 w-3.5 text-muted-foreground" />
        <div className="text-sm font-semibold">Recent activity</div>
      </div>
      <div className="divide-y divide-border max-h-64 overflow-y-auto">
        {items.map((e) => (
          <Link key={e.event_id} to="/tickets/$id" params={{ id: e.ticket_id }}
            className="flex items-start gap-3 px-4 py-2.5 text-xs hover:bg-accent/40 transition-colors">
            <div className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
            <div className="min-w-0">
              <div className="truncate font-medium text-foreground">{e.ticket_title}</div>
              <div className="text-muted-foreground">
                {e.event_type.replace(/_/g, " ")} — {e.new_value ?? ""}
              </div>
              <div className="text-[10px] text-muted-foreground">{new Date(e.created_at).toLocaleString()}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
