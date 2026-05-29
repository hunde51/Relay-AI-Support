import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { CommandPalette } from "./CommandPalette";
import { Sparkles } from "lucide-react";

export function AppShell({ children }: { children: ReactNode }) {
  const [cmdOpen, setCmdOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let gPressed = false;
    let gTimer: ReturnType<typeof setTimeout> | undefined;

    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const inField = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((v) => !v);
        return;
      }
      if (inField) return;

      if (e.key === "/") {
        e.preventDefault();
        setCmdOpen(true);
        return;
      }

      if (e.key.toLowerCase() === "g") {
        gPressed = true;
        clearTimeout(gTimer);
        gTimer = setTimeout(() => (gPressed = false), 900);
        return;
      }

      if (gPressed) {
        gPressed = false;
        const k = e.key.toLowerCase();
        if (k === "d") navigate({ to: "/" });
        else if (k === "t") navigate({ to: "/tickets" });
        else if (k === "a") navigate({ to: "/ai-insights" });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar onOpenCommand={() => setCmdOpen(true)} />
        <main className="flex-1 min-w-0">{children}</main>
      </div>
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
      <button
        title="AI assistant (coming soon)"
        className="fixed bottom-6 right-6 z-20 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 transition-transform hover:scale-105 active:scale-95"
      >
        <Sparkles className="h-5 w-5" />
      </button>
    </div>
  );
}
