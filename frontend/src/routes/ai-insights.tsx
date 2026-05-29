import { createFileRoute } from "@tanstack/react-router";
import { AutoResolveChart, CategoryPie, PeakHoursHeatmap, ResolutionTrendChart } from "@/components/charts/AnalyticsCharts";

export const Route = createFileRoute("/ai-insights")({
  head: () => ({
    meta: [
      { title: "AI Insights — AI SupportOps Hub" },
      { name: "description", content: "Analytics on ticket distribution, resolution trends, and AI auto-resolution performance." },
    ],
  }),
  component: AIInsights,
});

function AIInsights() {
  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1600px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">AI insights</h1>
        <p className="text-sm text-muted-foreground">How your support pipeline and AI agents are performing.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <CategoryPie />
        <ResolutionTrendChart />
        <AutoResolveChart />
        <PeakHoursHeatmap />
      </div>
    </div>
  );
}
