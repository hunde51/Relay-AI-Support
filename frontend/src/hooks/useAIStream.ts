import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api/client";

export type LiveStep = {
  step: "triage" | "rag_retrieve" | "decision" | "action";
  message: string;
  confidence?: number;
  decision?: string;
  response_preview?: string;
};

export function useAIStream(ticketId: string | null) {
  const [steps, setSteps] = useState<LiveStep[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!ticketId) return;
    setSteps([]);

    const ws = new WebSocket(`${WS_BASE}/ws/ai-stream/${ticketId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onmessage = (e) => setSteps((prev) => [...prev, JSON.parse(e.data)]);
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [ticketId]);

  return { steps, connected };
}
