import { motion } from "framer-motion";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from "recharts";

// Static placeholder data — will be replaced with real API in Phase 10
const categoryDistribution = [
  { key: "billing", name: "Billing", value: 34 },
  { key: "technical", name: "Technical", value: 28 },
  { key: "account", name: "Account", value: 19 },
  { key: "general", name: "General", value: 12 },
  { key: "feature", name: "Feature", value: 7 },
];
const resolutionTrend = [
  { day: "Mon", opened: 12, resolved: 9 },
  { day: "Tue", opened: 18, resolved: 14 },
  { day: "Wed", opened: 15, resolved: 16 },
  { day: "Thu", opened: 22, resolved: 18 },
  { day: "Fri", opened: 19, resolved: 21 },
  { day: "Sat", opened: 8, resolved: 10 },
  { day: "Sun", opened: 5, resolved: 7 },
];
const aiAutoResolveRate = [
  { week: "W1", rate: 42 }, { week: "W2", rate: 47 }, { week: "W3", rate: 51 },
  { week: "W4", rate: 55 }, { week: "W5", rate: 58 }, { week: "W6", rate: 63 },
  { week: "W7", rate: 68 }, { week: "W8", rate: 71 },
];
const peakHours = Array.from({ length: 7 }, (_, d) =>
  Array.from({ length: 24 }, (_, h) => ({
    day: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d],
    hour: h,
    v: Math.random() * 0.9,
  }))
).flat();

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

const tooltipStyle = {
  backgroundColor: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--popover-foreground)",
};

export function CategoryPie() {
  return (
    <ChartCard title="Ticket categories" subtitle="Distribution this week">
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={categoryDistribution}
            dataKey="value"
            nameKey="name"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
            stroke="var(--background)"
            strokeWidth={2}
            animationDuration={700}
          >
            {categoryDistribution.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--accent)" }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        {categoryDistribution.map((c, i) => (
          <div key={c.key} className="flex items-center gap-2 text-muted-foreground">
            <span className="h-2 w-2 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
            <span>{c.name}</span>
            <span className="ml-auto font-mono text-foreground">{c.value}</span>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

export function ResolutionTrendChart() {
  return (
    <ChartCard title="Resolution trend" subtitle="Opened vs. resolved · last 7 days">
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={resolutionTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="g-resolved" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="g-opened" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "var(--border)" }} />
          <Area type="monotone" dataKey="opened" stroke="var(--chart-1)" strokeWidth={2} fill="url(#g-opened)" />
          <Area type="monotone" dataKey="resolved" stroke="var(--chart-2)" strokeWidth={2} fill="url(#g-resolved)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AutoResolveChart() {
  return (
    <ChartCard title="AI auto-resolution rate" subtitle="Trending up · last 8 weeks">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={aiAutoResolveRate} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="week" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} unit="%" />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "var(--border)" }} />
          <Line type="monotone" dataKey="rate" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--primary)" }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function PeakHoursHeatmap() {
  const hours = Array.from({ length: 24 }, (_, h) => h);
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const get = (d: string, h: number) => peakHours.find((p) => p.day === d && p.hour === h)?.v ?? 0;

  return (
    <ChartCard title="Peak support hours" subtitle="UTC · ticket volume intensity">
      <div className="overflow-x-auto">
        <div className="min-w-[520px]">
          <div className="flex gap-1 pl-10 pb-1 text-[10px] text-muted-foreground">
            {hours.map((h) => (
              <div key={h} className="w-4 text-center">{h % 6 === 0 ? h : ""}</div>
            ))}
          </div>
          {days.map((d) => (
            <div key={d} className="flex items-center gap-1 mb-1">
              <div className="w-8 text-[10px] text-muted-foreground">{d}</div>
              <div className="flex gap-1">
                {hours.map((h) => {
                  const v = get(d, h);
                  return (
                    <div
                      key={h}
                      title={`${d} ${h}:00 — ${(v * 100).toFixed(0)}%`}
                      className="h-4 w-4 rounded-sm transition-transform hover:scale-125 hover:ring-1 hover:ring-primary"
                      style={{ background: `color-mix(in oklab, var(--primary) ${Math.round(v * 90)}%, var(--muted))` }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </ChartCard>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="rounded-xl border border-border bg-card p-5"
    >
      <div className="mb-4">
        <div className="text-sm font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
      </div>
      {children}
    </motion.div>
  );
}
