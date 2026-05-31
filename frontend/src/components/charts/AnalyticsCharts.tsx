import { motion } from "framer-motion";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
} from "recharts";
import {
  useAnalyticsCategories, useAnalyticsResolution,
  useAnalyticsAutoRate, useAnalyticsPeakHours,
} from "@/lib/queries";

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
const tooltipStyle = {
  backgroundColor: "var(--popover)", border: "1px solid var(--border)",
  borderRadius: 8, fontSize: 12, color: "var(--popover-foreground)",
};

export function CategoryPie() {
  const { data, isLoading } = useAnalyticsCategories();
  const items = (data ?? []).map((r, i) => ({ ...r, name: r.category, fill: COLORS[i % COLORS.length] }));

  return (
    <ChartCard title="Ticket categories" subtitle="Distribution all time" loading={isLoading}>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={items} dataKey="count" nameKey="name" innerRadius={55} outerRadius={85}
            paddingAngle={3} stroke="var(--background)" strokeWidth={2} animationDuration={700}>
            {items.map((c, i) => <Cell key={c.name} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        {items.map((c, i) => (
          <div key={c.name} className="flex items-center gap-2 text-muted-foreground">
            <span className="h-2 w-2 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
            <span className="capitalize">{c.name}</span>
            <span className="ml-auto font-mono text-foreground">{c.count}</span>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

export function ResolutionTrendChart() {
  const { data, isLoading } = useAnalyticsResolution();
  const items = (data ?? []).map((r) => ({ day: r.day.slice(5), count: r.count }));

  return (
    <ChartCard title="Resolution trend" subtitle="Resolved tickets · last 14 days" loading={isLoading}>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={items} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="g-resolved" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Area type="monotone" dataKey="count" stroke="var(--chart-2)" strokeWidth={2} fill="url(#g-resolved)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AutoResolveChart() {
  const { data, isLoading } = useAnalyticsAutoRate();
  const rate = data ? Math.round(data.rate * 100) : 0;

  return (
    <ChartCard title="AI auto-resolution rate" subtitle="Completed AI runs" loading={isLoading}>
      <div className="flex items-center justify-center gap-8 py-6">
        <div className="text-center">
          <div className="text-5xl font-bold text-primary">{rate}%</div>
          <div className="text-xs text-muted-foreground mt-1">auto-resolved</div>
        </div>
        <div className="text-xs space-y-2 text-muted-foreground">
          <div>Total runs: <span className="text-foreground font-mono">{data?.total_ai_runs ?? 0}</span></div>
          <div>Auto-resolved: <span className="text-foreground font-mono">{data?.auto_resolved ?? 0}</span></div>
        </div>
      </div>
    </ChartCard>
  );
}

export function PeakHoursHeatmap() {
  const { data, isLoading } = useAnalyticsPeakHours();
  const hours = Array.from({ length: 24 }, (_, h) => h);
  const maxCount = Math.max(1, ...(data ?? []).map((r) => r.count));
  const get = (h: number) => ((data ?? []).find((r) => r.hour === h)?.count ?? 0) / maxCount;

  return (
    <ChartCard title="Peak support hours" subtitle="UTC · ticket volume by hour" loading={isLoading}>
      <div className="overflow-x-auto">
        <div className="min-w-[400px]">
          <div className="flex gap-1 pb-1 text-[10px] text-muted-foreground">
            {hours.map((h) => <div key={h} className="w-5 text-center">{h % 6 === 0 ? h : ""}</div>)}
          </div>
          <div className="flex gap-1">
            {hours.map((h) => {
              const v = get(h);
              return (
                <div key={h} title={`${h}:00 — ${Math.round(v * 100)}%`}
                  className="h-8 w-5 rounded-sm transition-transform hover:scale-110"
                  style={{ background: `color-mix(in oklab, var(--primary) ${Math.round(v * 90)}%, var(--muted))` }} />
              );
            })}
          </div>
        </div>
      </div>
    </ChartCard>
  );
}

function ChartCard({ title, subtitle, children, loading }: {
  title: string; subtitle?: string; children: React.ReactNode; loading?: boolean;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4">
        <div className="text-sm font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
      </div>
      {loading ? <div className="h-40 rounded-lg shimmer" /> : children}
    </motion.div>
  );
}
