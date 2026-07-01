import { Bell, Search, ChevronDown, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface TopbarProps {
  onOpenCommand: () => void;
  onToggleMobileNav: () => void;
}

export function Topbar({ onOpenCommand, onToggleMobileNav }: TopbarProps) {
  const auth = useAuth();
  return (
    <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-background/80 px-3 backdrop-blur-md md:px-6 sticky top-0 z-30 safe-area-top">
      <button
        onClick={onToggleMobileNav}
        className="md:hidden flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-card hover:text-foreground -ml-1"
        aria-label="Toggle navigation menu"
      >
        <Menu className="h-4 w-4" />
      </button>

      <button
        onClick={onOpenCommand}
        className="group flex flex-1 max-w-md items-center gap-2 rounded-lg border border-border bg-card/60 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-card hover:text-foreground min-w-0"
      >
        <Search className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-left truncate">Search tickets, users, IDs…</span>
        <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground shrink-0">
          ⌘K
        </kbd>
      </button>

      <div className="flex items-center gap-1 md:gap-2 shrink-0">
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-card hover:text-foreground">
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
        </button>
        {auth.token ? (
          <>
            <button className="flex items-center gap-1.5 rounded-lg pl-1 pr-1.5 md:pr-2 py-1 transition-colors hover:bg-card" title={auth.organizationId ?? "unknown org"}>
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-primary/40 to-info/40 text-xs font-medium text-foreground">
                {(auth.userId ?? "AR").slice(0, 2).toUpperCase()}
              </div>
              <span className="hidden sm:block text-sm max-w-[120px] truncate">
                {auth.userId ?? "Signed in"}
              </span>
              <ChevronDown className="hidden sm:block h-3.5 w-3.5 text-muted-foreground shrink-0" />
            </button>
            <button onClick={() => auth.logout()} className="rounded bg-red-600 px-2 md:px-3 py-1 text-white text-xs md:text-sm">Logout</button>
          </>
        ) : (
          <button
            onClick={async () => {
              const userId = prompt("User ID", "dev-user");
              if (!userId) return;
              const org = prompt("Organization ID", "org-default");
              if (!org) return;
              const role = prompt("Role", "agent") || "agent";
              try {
                const resp = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/auth/token`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ user_id: userId, organization_id: org, role }),
                });
                const body = await resp.json();
                if (resp.ok && body.access_token) {
                  auth.login({
                    token: body.access_token,
                    userId: body.user_id ?? userId,
                    organizationId: body.organization_id ?? org,
                    role: body.role ?? role,
                  });
                  window.location.reload();
                } else {
                  alert("Login failed");
                }
              } catch (e) {
                alert("Login error");
              }
            }}
            className="rounded bg-primary px-2 md:px-3 py-1 text-white text-xs md:text-sm"
          >
            Login
          </button>
        )}
      </div>
    </header>
  );
}
