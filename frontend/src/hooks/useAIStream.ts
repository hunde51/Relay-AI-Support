import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api/client";

export type LiveStep = {
  step: "triage" | "rag_retrieve" | "decision" | "action" | "tool_call";
  message: string;
  confidence?: number;
  decision?: string;
  response_preview?: string;
  // tool call payload
  tool?: {
    id: string;
    tool_name: string;
    status: string;
    result?: any;
    error?: string;
    suggested_action_id?: string;
  };
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
    ws.onmessage = (e) => {
      const payload = JSON.parse(e.data);
      if (payload.tool_call) {
        setSteps((prev) => [...prev, { step: "tool_call", message: payload.tool_call.tool_name, tool: payload.tool_call }]);
      } else {
        setSteps((prev) => [...prev, payload]);
      }
    };
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [ticketId]);

  return { steps, connected };
}
