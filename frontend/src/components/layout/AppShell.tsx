import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Sidebar } from "./Sidebar";
import { MobileSidebar } from "./MobileSidebar";
import { Topbar } from "./Topbar";
import { CommandPalette } from "./CommandPalette";
import { Sparkles } from "lucide-react";

export function AppShell({ children }: { children: ReactNode }) {
  const [cmdOpen, setCmdOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let gPressed = false;
    let gTimer: ReturnType<typeof setTimeout> | undefined;

    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const inField =
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

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
    <div className="flex min-h-screen w-full bg-background text-foreground overflow-x-hidden">
      <Sidebar />
      <MobileSidebar open={mobileNavOpen} onOpenChange={setMobileNavOpen} />
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar onOpenCommand={() => setCmdOpen(true)} onToggleMobileNav={() => setMobileNavOpen((v) => !v)} />
        <main className="flex-1 min-w-0">{children}</main>
      </div>
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
      <button
        title="AI assistant (coming soon)"
        className="fixed bottom-4 right-4 md:bottom-6 md:right-6 z-20 flex h-11 w-11 md:h-12 md:w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 transition-transform hover:scale-105 active:scale-95"
      >
        <Sparkles className="h-4 w-4 md:h-5 md:w-5" />
      </button>
    </div>
  );
}
