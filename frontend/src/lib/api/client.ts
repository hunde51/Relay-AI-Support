const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, body);
  }

  return body as T;
}

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "critical";
export type TicketCategory = "billing" | "technical" | "general" | "account";

export type ApiTicket = {
  id: string;
  title: string;
  message: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  created_at: string;
};

export type TicketCreate = {
  title: string;
  message: string;
  priority?: TicketPriority;
  category?: TicketCategory;
};

export type TicketUpdate = {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
};

export const api = {
  tickets: {
    list: (): Promise<ApiTicket[]> => request<ApiTicket[]>(`${BASE}/tickets`),

    get: (id: string): Promise<ApiTicket> => request<ApiTicket>(`${BASE}/tickets/${id}`),

    create: (data: TicketCreate): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),

    update: (id: string, data: TicketUpdate): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
  },

  agent: {
    process: (ticketId: string) => request(`${BASE}/agent/process/${ticketId}`, { method: "POST" }),

    logs: (ticketId: string) => request(`${BASE}/agent/logs/${ticketId}`),
  },
};
