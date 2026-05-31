import type { TicketStatus, TicketPriority, TicketCategory } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

const statusStyles: Record<TicketStatus, string> = {
  open: "bg-info/15 text-info border-info/30",
  in_progress: "bg-warning/15 text-warning border-warning/30",
  resolved: "bg-success/15 text-success border-success/30",
  closed: "bg-muted/60 text-muted-foreground border-border",
};

const statusLabel: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <motion.span
      layout
      key={status}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors",
        statusStyles[status],
      )}
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inset-0 rounded-full bg-current opacity-60 animate-ping" />
        <span className="relative h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      {statusLabel[status]}
    </motion.span>
  );
}

const priorityStyles: Record<TicketPriority, string> = {
  low: "bg-muted/60 text-muted-foreground border-border",
  medium: "bg-info/10 text-info border-info/25",
  high: "bg-warning/10 text-warning border-warning/30",
  critical: "bg-destructive/15 text-destructive border-destructive/30",
};

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        priorityStyles[priority],
      )}
    >
      {priority}
    </span>
  );
}

const categoryStyles: Record<TicketCategory, string> = {
  billing: "bg-chart-1/15 text-chart-1",
  technical: "bg-destructive/15 text-destructive",
  general: "bg-muted/60 text-muted-foreground",
  account: "bg-chart-4/15 text-chart-4",
};

export function CategoryBadge({ category }: { category: TicketCategory }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-md px-2 py-0.5 text-[11px] font-medium capitalize",
        categoryStyles[category],
      )}
    >
      {category}
    </span>
  );
}
