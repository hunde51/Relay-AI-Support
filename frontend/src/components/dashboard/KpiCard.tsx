import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: number;
  suffix?: string;
  delta?: string;
  trend?: "up" | "down" | "flat";
  icon: React.ReactNode;
  loading?: boolean;
  decimals?: number;
  index?: number;
}

function useCountUp(target: number, duration = 900, decimals = 0) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(target * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else setV(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString();
}

export function KpiCard({ label, value, suffix, delta, trend = "up", icon, loading, decimals = 0, index = 0 }: KpiCardProps) {
  const display = useCountUp(loading ? 0 : value, 900, decimals);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: "easeOut" }}
      whileHover={{ y: -2 }}
      className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/30"
    >
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
      </div>
      <div className="mt-4 flex items-baseline gap-1.5">
        {loading ? (
          <div className="h-8 w-24 rounded shimmer" />
        ) : (
          <>
            <div className="text-3xl font-semibold tracking-tight">{display}</div>
            {suffix && <div className="text-sm text-muted-foreground">{suffix}</div>}
          </>
        )}
      </div>
      {delta && !loading && (
        <div
          className={cn(
            "mt-2 inline-flex items-center gap-1 text-xs",
            trend === "up" && "text-success",
            trend === "down" && "text-destructive",
            trend === "flat" && "text-muted-foreground",
          )}
        >
          <span>{trend === "up" ? "↑" : trend === "down" ? "↓" : "·"}</span>
          <span>{delta}</span>
          <span className="text-muted-foreground">vs last week</span>
        </div>
      )}
      <div className="pointer-events-none absolute -bottom-12 -right-12 h-32 w-32 rounded-full bg-primary/5 blur-2xl opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
    </motion.div>
  );
}
