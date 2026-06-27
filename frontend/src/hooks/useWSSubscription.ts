import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WS_BASE } from "@/lib/api/client";
import { keys } from "@/lib/queries";

const RECONNECT_BASE = 1000;
const RECONNECT_MAX = 30_000;

export function useWSSubscription(path: string) {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const connect = () => {
    const ws = new WebSocket(`${WS_BASE}${path}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retriesRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "ticket_created" || msg.type === "ticket_updated" || msg.type === "ticket_resolved") {
          qc.invalidateQueries({ queryKey: ["tickets"] });
          qc.invalidateQueries({ queryKey: keys.dashboardSummary });
          qc.invalidateQueries({ queryKey: keys.recentActivity });
        }
        if (msg.type?.startsWith("ai_")) {
          qc.invalidateQueries({ queryKey: ["ticket", msg.ticket_id, "actions"] });
        }
        if (msg.type === "knowledge.document_ingested") {
          qc.invalidateQueries({ queryKey: keys.kbDocuments });
        }
      } catch {
        // ignore malformed
      }
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(RECONNECT_BASE * Math.pow(2, retriesRef.current), RECONNECT_MAX);
      retriesRef.current += 1;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  };

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [path]);

  return connected;
}
