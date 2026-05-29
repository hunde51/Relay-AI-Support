export const kpis = {
  totalTickets: 128,
  openTickets: 32,
  resolvedToday: 18,
  avgResponseMin: 2.4,
};

export const categoryDistribution = [
  { name: "Billing", value: 34, key: "billing" },
  { name: "Bug", value: 41, key: "bug" },
  { name: "General", value: 28, key: "general" },
  { name: "Account", value: 15, key: "account" },
  { name: "Feature", value: 10, key: "feature" },
];

export const resolutionTrend = [
  { day: "Mon", resolved: 22, opened: 28 },
  { day: "Tue", resolved: 26, opened: 24 },
  { day: "Wed", resolved: 31, opened: 30 },
  { day: "Thu", resolved: 28, opened: 33 },
  { day: "Fri", resolved: 35, opened: 29 },
  { day: "Sat", resolved: 18, opened: 14 },
  { day: "Sun", resolved: 14, opened: 12 },
];

export const aiAutoResolveRate = [
  { week: "W1", rate: 41 },
  { week: "W2", rate: 47 },
  { week: "W3", rate: 52 },
  { week: "W4", rate: 58 },
  { week: "W5", rate: 61 },
  { week: "W6", rate: 64 },
  { week: "W7", rate: 67 },
  { week: "W8", rate: 71 },
];

// 7 days x 24 hours heatmap (intensity 0..1)
export const peakHours: { day: string; hour: number; v: number }[] = (() => {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const rows: { day: string; hour: number; v: number }[] = [];
  for (const d of days) {
    for (let h = 0; h < 24; h++) {
      // peak 9–18, lighter weekends
      const base = h >= 9 && h <= 18 ? 0.55 + Math.sin((h - 9) / 9 * Math.PI) * 0.35 : 0.12;
      const weekend = d === "Sat" || d === "Sun" ? 0.55 : 1;
      const jitter = ((h * 7 + d.charCodeAt(0)) % 17) / 80;
      rows.push({ day: d, hour: h, v: Math.max(0.05, Math.min(1, base * weekend + jitter)) });
    }
  }
  return rows;
})();
