import { motion } from "framer-motion";
import { Brain, BookOpen, GitBranch, Rocket } from "lucide-react";
import type { LiveStep } from "@/hooks/useAIStream";
import { cn } from "@/lib/utils";

// Map backend step names → UI
const kindMap: Record<string, "triage" | "rag" | "decision" | "action" | "tool"> = {
  triage: "triage",
  rag_retrieve: "rag",
  decision: "decision",
  action: "action",
  tool_call: "tool",
};

const iconMap = {
  triage: <Brain className="h-3.5 w-3.5" />,
  rag: <BookOpen className="h-3.5 w-3.5" />,
  decision: <GitBranch className="h-3.5 w-3.5" />,
  action: <Rocket className="h-3.5 w-3.5" />,
  tool: <BookOpen className="h-3.5 w-3.5" />,
};

const tone = {
  triage: "text-info border-info/40 bg-info/10",
  rag: "text-chart-2 border-chart-2/40 bg-chart-2/10",
  decision: "text-warning border-warning/40 bg-warning/10",
  action: "text-success border-success/40 bg-success/10",
  tool: "text-muted-foreground border-border/40 bg-background",
};

const agentName = {
  triage: "Triage Agent",
  rag: "Knowledge Agent",
  decision: "Decision Agent",
  action: "Action Agent",
  tool: "Tool",
};

type Props = {
  liveSteps?: LiveStep[];
  connected?: boolean;
};

export function AIActivityPanel({ liveSteps = [], connected }: Props) {
  const items = liveSteps.map((s, i) => {
    const kind = kindMap[s.step] ?? "triage";
    return {
      id: `live-${i}`,
      kind,
      title: s.message,
      agent: agentName[kind],
      confidence: s.confidence ?? 1,
      summary: s.tool ? (s.tool.status === "suggested" ? `Suggested action: ${s.tool.suggested_action_id}` : (s.tool.status === "failed" ? `Error: ${s.tool.error}` : JSON.stringify(s.tool.result ?? {}).slice(0, 80))) : (s.decision ? `Decision: ${s.decision}` : (s.response_preview ?? "")),
    };
  });

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <div className="text-sm font-semibold">AI Activity</div>
          <div className="text-xs text-muted-foreground">Live reasoning pipeline</div>
        </div>
        <div
          className={cn(
            "flex items-center gap-1.5 text-xs",
            connected ? "text-success" : "text-muted-foreground",
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              connected ? "bg-success animate-pulse" : "bg-muted-foreground",
            )}
          />
          {connected ? "live" : "waiting"}
        </div>
      </div>

      <div className="relative px-4 py-4">
        <div className="absolute left-[27px] top-4 bottom-4 w-px bg-border" />
        <ol className="space-y-3">
          {items.length === 0 && (
            <li className="text-xs text-muted-foreground pl-10">Waiting for agent to start…</li>
          )}
          {items.map((s, i) => (
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
                    "relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-background",
                    tone[s.kind],
                  )}
                >
                  {iconMap[s.kind]}
                </div>
                <div className="min-w-0 flex-1 pb-1">
                  <div className="truncate text-sm font-medium">{s.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {s.agent} · {s.summary}
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${Math.round(s.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {Math.round(s.confidence * 100)}%
                    </span>
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
