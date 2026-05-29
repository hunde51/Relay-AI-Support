import { motion } from "framer-motion";
import { Brain, BookOpen, GitBranch, Rocket } from "lucide-react";
import { aiActivity, type AIStep, type AIStepKind } from "@/data/mockAIActivity";
import { cn } from "@/lib/utils";

const iconMap: Record<AIStepKind, React.ReactNode> = {
  triage: <Brain className="h-3.5 w-3.5" />,
  rag: <BookOpen className="h-3.5 w-3.5" />,
  decision: <GitBranch className="h-3.5 w-3.5" />,
  action: <Rocket className="h-3.5 w-3.5" />,
};

const tone: Record<AIStepKind, string> = {
  triage: "text-info border-info/40 bg-info/10",
  rag: "text-chart-2 border-chart-2/40 bg-chart-2/10",
  decision: "text-warning border-warning/40 bg-warning/10",
  action: "text-success border-success/40 bg-success/10",
};

export function AIActivityPanel({ steps = aiActivity }: { steps?: AIStep[] }) {
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <div className="text-sm font-semibold">AI Activity</div>
          <div className="text-xs text-muted-foreground">Live reasoning pipeline</div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-success">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
          live
        </div>
      </div>

      <div className="relative px-4 py-4">
        <div className="absolute left-[27px] top-4 bottom-4 w-px bg-border" />
        <ol className="space-y-3">
          {steps.map((s, i) => (
            <motion.li
              key={s.id}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, delay: i * 0.08, ease: "easeOut" }}
              className="group relative"
            >
              <div className="flex gap-3">
                <div
                  className={cn(
                    "relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-background transition-shadow",
                    tone[s.kind],
                    "group-hover:shadow-[0_0_0_4px_color-mix(in_oklab,currentColor_15%,transparent)]",
                  )}
                >
                  {iconMap[s.kind]}
                </div>
                <div className="min-w-0 flex-1 pb-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-sm font-medium">{s.title}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{s.ticketId}</div>
                  </div>
                  <div className="text-xs text-muted-foreground">{s.agent} · {s.summary}</div>

                  {/* hover reveal */}
                  <div className="max-h-0 overflow-hidden opacity-0 transition-all duration-300 ease-out group-hover:max-h-80 group-hover:opacity-100 group-hover:mt-2">
                    <div className="rounded-lg border border-border bg-background/60 p-3 text-xs space-y-2">
                      <p className="text-muted-foreground leading-relaxed">{s.reasoning}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Confidence</span>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${Math.round(s.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[10px]">{Math.round(s.confidence * 100)}%</span>
                      </div>
                      {s.snippets && (
                        <div className="space-y-1.5 pt-1">
                          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                            Retrieved knowledge
                          </div>
                          {s.snippets.map((sn) => (
                            <div key={sn.title} className="rounded-md border border-border bg-card/60 p-2">
                              <div className="text-xs font-medium">{sn.title}</div>
                              <div className="font-mono text-[10px] text-muted-foreground">{sn.source}</div>
                              <div className="mt-1 text-[11px] text-muted-foreground line-clamp-2">{sn.excerpt}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </motion.li>
          ))}
        </ol>
      </div>
    </div>
  );
}
