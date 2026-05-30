const BASE = "http://localhost:8000";

export type ApiTicket = {
  id: string;
  title: string;
  message: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
};

export type TicketCreate = {
  title: string;
  message: string;
  priority?: string;
  category?: string;
};

export type TicketUpdate = {
  status?: string;
  priority?: string;
  category?: string;
};

export const api = {
  tickets: {
    list: (): Promise<ApiTicket[]> =>
      fetch(`${BASE}/tickets`).then((r) => r.json()),

    get: (id: string): Promise<ApiTicket> =>
      fetch(`${BASE}/tickets/${id}`).then((r) => r.json()),

    create: (data: TicketCreate): Promise<ApiTicket> =>
      fetch(`${BASE}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then((r) => r.json()),

    update: (id: string, data: TicketUpdate): Promise<ApiTicket> =>
      fetch(`${BASE}/tickets/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then((r) => r.json()),
  },

  agent: {
    process: (ticketId: string) =>
      fetch(`${BASE}/agent/process/${ticketId}`, { method: "POST" }).then((r) => r.json()),

    logs: (ticketId: string) =>
      fetch(`${BASE}/agent/logs/${ticketId}`).then((r) => r.json()),
  },
};
