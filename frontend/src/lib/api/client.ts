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
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

export type TicketStatus = "open" | "in_progress" | "waiting_on_customer" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "critical";
export type TicketCategory = "billing" | "technical" | "general" | "account";

export type ApiTicket = {
  id: string;
  title: string;
  message: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  source: string;
  sentiment: string | null;
  summary: string | null;
  organization_id: string | null;
  customer_id: string | null;
  assignee_id: string | null;
  sla_due_at: string | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PaginatedTickets = {
  items: ApiTicket[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
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

export type ApiMessage = {
  id: string;
  ticket_id: string;
  sender_type: string;
  sender_user_id: string | null;
  sender_customer_id: string | null;
  body: string;
  is_internal: boolean;
  created_at: string;
  updated_at: string;
};

export type ApiEvent = {
  id: string;
  ticket_id: string;
  actor_type: string;
  actor_user_id: string | null;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type DashboardSummary = {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_today: number;
  avg_first_response_minutes: number | null;
};

export type WorkspaceSettings = {
  id: string;
  name: string;
  plan: string;
  region: string;
};

export type AISettings = {
  ai_enabled: boolean;
  auto_resolve_enabled: boolean;
  human_approval_threshold: string;
};

export type NotificationSettings = {
  email_digest_enabled: boolean;
  slack_alerts_enabled: boolean;
  sms_incidents_enabled: boolean;
};

export const api = {
  tickets: {
    list: (params?: {
      status?: TicketStatus;
      priority?: TicketPriority;
      category?: TicketCategory;
      search?: string;
      page?: number;
      page_size?: number;
    }): Promise<PaginatedTickets> => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.priority) q.set("priority", params.priority);
      if (params?.category) q.set("category", params.category);
      if (params?.search) q.set("search", params.search);
      if (params?.page) q.set("page", String(params.page));
      if (params?.page_size) q.set("page_size", String(params.page_size));
      const qs = q.toString();
      return request<PaginatedTickets>(`${BASE}/tickets${qs ? `?${qs}` : ""}`);
    },

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

    resolve: (id: string): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets/${id}/resolve`, { method: "POST" }),

    escalate: (id: string): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets/${id}/escalate`, { method: "POST" }),

    messages: (id: string): Promise<ApiMessage[]> =>
      request<ApiMessage[]>(`${BASE}/tickets/${id}/messages`),

    addMessage: (
      id: string,
      data: { body: string; is_internal?: boolean; sender_type?: string },
    ): Promise<ApiMessage> =>
      request<ApiMessage>(`${BASE}/tickets/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),

    timeline: (id: string): Promise<ApiEvent[]> =>
      request<ApiEvent[]>(`${BASE}/tickets/${id}/timeline`),
  },

  dashboard: {
    summary: (): Promise<DashboardSummary> =>
      request<DashboardSummary>(`${BASE}/dashboard/summary`),
    recentActivity: () => request<unknown[]>(`${BASE}/dashboard/recent-activity`),
  },

  analytics: {
    categories: () => request<{ category: string; count: number }[]>(`${BASE}/analytics/categories`),
    resolutionTrend: () => request<{ day: string; count: number }[]>(`${BASE}/analytics/resolution-trend`),
    autoResolutionRate: () => request<{ total_ai_runs: number; auto_resolved: number; rate: number }>(`${BASE}/analytics/auto-resolution-rate`),
    peakHours: () => request<{ hour: number; count: number }[]>(`${BASE}/analytics/peak-hours`),
    slaPerformance: () => request<{ total_with_sla: number; met: number; breached: number }>(`${BASE}/analytics/sla-performance`),
    agentPerformance: () => request<{ decision: string; count: number }[]>(`${BASE}/analytics/agent-performance`),
  },

  knowledge: {
    sources: () => request<unknown[]>(`${BASE}/knowledge/sources`),
    documents: () => request<unknown[]>(`${BASE}/knowledge/documents`),
    search: (query: string, top_k = 4) =>
      request<{ query: string; results: unknown[] }>(`${BASE}/knowledge/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k }),
      }),
    ingest: (documentId: string) =>
      request(`${BASE}/knowledge/documents/${documentId}/ingest`, { method: "POST" }),
  },

  settings: {
    workspace: (): Promise<WorkspaceSettings> =>
      request<WorkspaceSettings>(`${BASE}/settings/workspace`),
    patchWorkspace: (data: Partial<WorkspaceSettings>): Promise<WorkspaceSettings> =>
      request<WorkspaceSettings>(`${BASE}/settings/workspace`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    ai: (): Promise<AISettings> => request<AISettings>(`${BASE}/settings/ai`),
    patchAI: (data: Partial<AISettings>): Promise<AISettings> =>
      request<AISettings>(`${BASE}/settings/ai`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    notifications: (): Promise<NotificationSettings> =>
      request<NotificationSettings>(`${BASE}/settings/notifications`),
    patchNotifications: (data: Partial<NotificationSettings>): Promise<NotificationSettings> =>
      request<NotificationSettings>(`${BASE}/settings/notifications`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
  },

  ai: {
    run: (ticketId: string) =>
      request(`${BASE}/ai/tickets/${ticketId}/run`, { method: "POST" }),
    runs: (ticketId: string) => request<unknown[]>(`${BASE}/ai/tickets/${ticketId}/runs`),
    steps: (runId: string) => request<unknown[]>(`${BASE}/ai/runs/${runId}/steps`),
    suggestedActions: (ticketId: string) =>
      request<unknown[]>(`${BASE}/ai/tickets/${ticketId}/suggested-actions`),
    approve: (actionId: string) =>
      request(`${BASE}/ai/actions/${actionId}/approve`, { method: "POST" }),
    reject: (actionId: string) =>
      request(`${BASE}/ai/actions/${actionId}/reject`, { method: "POST" }),
    executeAction: (actionId: string) =>
      request(`${BASE}/ai/actions/${actionId}/execute`, { method: "POST" }),
  },

  // Legacy — kept for backward compat with agent.py route
  agent: {
    process: (ticketId: string) =>
      request(`${BASE}/ai/tickets/${ticketId}/run`, { method: "POST" }),
    logs: (ticketId: string) => request(`${BASE}/agent/logs/${ticketId}`),
  },
};
