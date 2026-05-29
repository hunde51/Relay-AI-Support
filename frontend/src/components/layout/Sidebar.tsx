import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Ticket, Sparkles, BookOpen, Settings, Headphones } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/tickets", label: "Tickets", icon: Ticket },
  { to: "/ai-insights", label: "AI Insights", icon: Sparkles },
  { to: "/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const path = useRouterState({ select: (r) => r.location.pathname });

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center gap-2 px-5 border-b border-sidebar-border">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Headphones className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">SupportOps</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">AI Hub</div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map((item) => {
          const active = item.exact ? path === item.to : path === item.to || path.startsWith(item.to + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/60",
              )}
            >
              {active && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-primary" />
              )}
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-sidebar-border">
        <div className="rounded-lg bg-sidebar-accent/50 p-3 text-xs text-muted-foreground">
          <div className="font-medium text-sidebar-foreground mb-1">AI assist online</div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
            4 agents active
          </div>
        </div>
      </div>
    </aside>
  );
}
