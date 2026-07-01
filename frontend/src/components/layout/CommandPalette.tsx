import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { Search, ArrowRight, Command as CmdIcon } from "lucide-react";
import { api, type ApiTicket } from "@/lib/api/client";

const shortcuts: { keys: string[]; label: string; to?: string }[] = [
  { keys: ["G", "D"], label: "Go to Dashboard", to: "/" },
  { keys: ["G", "T"], label: "Go to Tickets", to: "/tickets" },
  { keys: ["G", "A"], label: "Go to AI Insights", to: "/ai-insights" },
  { keys: ["/"], label: "Focus search" },
  { keys: ["Esc"], label: "Close panel" },
];

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [tickets, setTickets] = useState<ApiTicket[]>([]);

  useEffect(() => {
    api.tickets
      .list()
      .then((data) => setTickets(data.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onOpenChange(false);
    }
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const filtered = tickets
    .filter((t) => [t.id, t.title, t.category].join(" ").toLowerCase().includes(q.toLowerCase()))
    .slice(0, 6);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-background/60 backdrop-blur-sm pt-[8vh] md:pt-[10vh] px-2 md:px-4"
          onClick={() => onOpenChange(false)}
        >
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
            className="w-full md:max-w-xl mx-auto overflow-hidden rounded-xl border border-border bg-popover shadow-2xl md:max-h-[80vh] max-h-[90vh] flex flex-col"
          >
            <div className="flex items-center gap-3 border-b border-border px-4 py-3 shrink-0">
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search tickets, customers, IDs…"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground min-w-0"
              />
              <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground shrink-0">
                Esc
              </kbd>
            </div>

            <div className="overflow-y-auto p-2 flex-1">
              {filtered.length > 0 ? (
                <div className="mb-2">
                  <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                    Tickets
                  </div>
                  {filtered.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        navigate({ to: "/tickets/$id", params: { id: t.id } });
                        onOpenChange(false);
                      }}
                      className="group flex w-full items-center justify-between gap-3 rounded-md px-2 py-2.5 text-left text-sm transition-colors hover:bg-accent"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="font-mono text-xs text-muted-foreground shrink-0">{t.id}</span>
                        <span className="truncate">{t.title}</span>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100 shrink-0" />
                    </button>
                  ))}
                </div>
              ) : (
                <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                  No results
                </div>
              )}

              <div className="mt-2 border-t border-border pt-2">
                <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                  Shortcuts
                </div>
                {shortcuts.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => {
                      if (s.to) {
                        navigate({ to: s.to });
                        onOpenChange(false);
                      }
                    }}
                    className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-2.5 text-left text-sm transition-colors hover:bg-accent"
                  >
                    <span className="flex items-center gap-2 text-muted-foreground min-w-0">
                      <CmdIcon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{s.label}</span>
                    </span>
                    <span className="flex items-center gap-1 shrink-0">
                      {s.keys.map((k) => (
                        <kbd
                          key={k}
                          className="rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground"
                        >
                          {k}
                        </kbd>
                      ))}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
