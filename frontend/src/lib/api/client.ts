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
  const headers = new Headers(init?.headers as HeadersInit);
  const token = typeof window !== "undefined" ? (localStorage.getItem("VITE_CURRENT_USER_TOKEN") ?? import.meta.env.VITE_CURRENT_USER_TOKEN) : import.meta.env.VITE_CURRENT_USER_TOKEN;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(input, { ...(init ?? {}), headers });
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
  auto_resolution_rate?: number;
};

export type ApiKnowledgeSource = {
  id: string;
  name: string;
  source_type: string;
  status: string;
  created_at: string;
};

export type ApiKnowledgeChunk = {
  id: string;
  chunk_index: string;
  content: string;
  token_count: string | null;
  content_hash: string;
  created_at: string;
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

export type RecentActivity = {
  event_id: string;
  ticket_id: string;
  ticket_title: string;
  event_type: string;
  actor_type: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
};

export type ApiKeyWithSecret = ApiKey & { key: string };

export type WebhookEndpoint = {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
};

export type WebhookEndpointWithSecret = WebhookEndpoint & { secret: string };

export type ApiCustomer = {
  id: string;
  name: string;
  email: string;
  company: string | null;
  external_id: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
};

export type ApiCustomerTicket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
};

export type WebhookDelivery = {
  id: string;
  endpoint_id: string;
  event_type: string;
  status: string;
  attempts: number;
  response_status: number | null;
  created_at: string;
};

export type WidgetKey = {
  id: string;
  name: string;
  key_prefix: string;
  allowed_origins: string[] | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
};

export type WidgetKeyWithSecret = WidgetKey & { key: string };

export type Invitation = {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
  created_at: string;
};

export type TeamMember = {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type InviteValidateResponse = {
  valid: boolean;
  email?: string;
  organization_name?: string;
  role?: string;
  expires_at?: string;
  message?: string;
};

export type InviteAcceptResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  organization_id: string;
  role: string;
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

    close: (id: string): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets/${id}/close`, { method: "POST" }),

    assign: (id: string, assigneeId: string): Promise<ApiTicket> =>
      request<ApiTicket>(`${BASE}/tickets/${id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignee_id: assigneeId }),
      }),
  },

  dashboard: {
    summary: (): Promise<DashboardSummary> =>
      request<DashboardSummary>(`${BASE}/dashboard/summary`),
    recentActivity: (): Promise<RecentActivity[]> =>
      request<RecentActivity[]>(`${BASE}/dashboard/recent-activity`),
    ticketVolume: () => request<{ day: string; count: number }[]>(`${BASE}/dashboard/ticket-volume`),
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
    sources: () => request<ApiKnowledgeSource[]>(`${BASE}/knowledge/sources`),
    documents: () => request<unknown[]>(`${BASE}/knowledge/documents`),
    chunks: (documentId: string) => request<ApiKnowledgeChunk[]>(`${BASE}/knowledge/documents/${documentId}/chunks`),
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
    plan: (): Promise<{ plan: string; limits: Record<string, number | null>; usage_vs_limits: { usage: Record<string, number>; limits: Record<string, number>; remaining: Record<string, number> } }> =>
      request(`${BASE}/settings/plan`),
    patchPlan: (data: { plan?: string; monthly_ticket_limit?: number | null; api_rate_limit?: number | null; max_knowledge_docs?: number | null }): Promise<{ plan: string; limits: Record<string, number | null> }> =>
      request(`${BASE}/settings/plan`, {
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
    approve: (actionId: string, actorUserId?: string) =>
      request(`${BASE}/ai/actions/${actionId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_user_id: actorUserId ?? import.meta.env.VITE_CURRENT_USER_ID ?? null }),
      }),
    reject: (actionId: string, actorUserId?: string) =>
      request(`${BASE}/ai/actions/${actionId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_user_id: actorUserId ?? import.meta.env.VITE_CURRENT_USER_ID ?? null }),
      }),
    executeAction: (actionId: string, executorUserId?: string) =>
      request(`${BASE}/ai/actions/${actionId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ executor_user_id: executorUserId ?? import.meta.env.VITE_CURRENT_USER_ID ?? null }),
      }),
    audits: (ticketId: string) => request(`${BASE}/ai/tickets/${ticketId}/audits`),
  },

  customers: {
    list: (search?: string): Promise<ApiCustomer[]> => {
      const q = search ? `?search=${encodeURIComponent(search)}` : "";
      return request<ApiCustomer[]>(`${BASE}/customers${q}`);
    },
    get: (id: string): Promise<ApiCustomer> =>
      request<ApiCustomer>(`${BASE}/customers/${id}`),
    getTickets: (id: string): Promise<ApiCustomerTicket[]> =>
      request<ApiCustomerTicket[]>(`${BASE}/customers/${id}/tickets`),
    getTimeline: (id: string): Promise<RecentActivity[]> =>
      request<RecentActivity[]>(`${BASE}/customers/${id}/timeline`),
  },

  apiKeys: {
    list: (): Promise<ApiKey[]> => request<ApiKey[]>(`${BASE}/api-keys`),
    create: (data: { name: string; scopes?: string[] }): Promise<ApiKeyWithSecret> =>
      request<ApiKeyWithSecret>(`${BASE}/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    revoke: (id: string): Promise<void> =>
      request<void>(`${BASE}/api-keys/${id}`, { method: "DELETE" }),
    rotate: (id: string): Promise<ApiKeyWithSecret> =>
      request<ApiKeyWithSecret>(`${BASE}/api-keys/${id}/rotate`, { method: "POST" }),
  },

  webhooks: {
    listEndpoints: (): Promise<WebhookEndpoint[]> =>
      request<WebhookEndpoint[]>(`${BASE}/webhooks/endpoints`),
    createEndpoint: (data: { url: string; events: string[] }): Promise<WebhookEndpointWithSecret> =>
      request<WebhookEndpointWithSecret>(`${BASE}/webhooks/endpoints`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    deleteEndpoint: (id: string): Promise<void> =>
      request<void>(`${BASE}/webhooks/endpoints/${id}`, { method: "DELETE" }),
    listDeliveries: (): Promise<WebhookDelivery[]> =>
      request<WebhookDelivery[]>(`${BASE}/webhooks/deliveries`),
    testEndpoint: (id: string): Promise<{ delivery_id: string; status: string }> =>
      request<{ delivery_id: string; status: string }>(`${BASE}/webhooks/endpoints/${id}/test`, { method: "POST" }),
  },

  widgetKeys: {
    list: (): Promise<WidgetKey[]> => request<WidgetKey[]>(`${BASE}/settings/widget`),
    create: (data: { name: string; allowed_origins?: string[] }): Promise<WidgetKeyWithSecret> =>
      request<WidgetKeyWithSecret>(`${BASE}/settings/widget`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { name?: string; allowed_origins?: string[] }): Promise<WidgetKey> =>
      request<WidgetKey>(`${BASE}/settings/widget/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    revoke: (id: string): Promise<void> =>
      request<void>(`${BASE}/settings/widget/${id}`, { method: "DELETE" }),
  },

  invitations: {
    list: (): Promise<Invitation[]> => request<Invitation[]>(`${BASE}/invitations`),
    create: (data: { email: string; role: string }): Promise<Invitation> =>
      request<Invitation>(`${BASE}/invitations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    revoke: (id: string): Promise<void> =>
      request<void>(`${BASE}/invitations/${id}`, { method: "DELETE" }),
    validate: (token: string): Promise<InviteValidateResponse> =>
      request<InviteValidateResponse>(`${BASE}/invitations/validate/${encodeURIComponent(token)}`),
    accept: (data: { token: string; name: string; password: string }): Promise<InviteAcceptResponse> =>
      request<InviteAcceptResponse>(`${BASE}/invitations/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    members: (): Promise<TeamMember[]> => request<TeamMember[]>(`${BASE}/invitations/members`),
  },

  usage: {
    summary: (period?: string): Promise<{ period: string; tickets_created: number; ai_runs_executed: number; llm_prompt_tokens: number; llm_completion_tokens: number; llm_total_tokens: number; llm_cost_usd: number; api_requests: number; knowledge_chunks: number; active_users: number }> => {
      const q = period ? `?period=${encodeURIComponent(period)}` : "";
      return request(`${BASE}/usage/summary${q}`);
    },
    history: (months = 12): Promise<{ period: string; tickets_created: number; ai_runs_executed: number; llm_prompt_tokens: number; llm_completion_tokens: number; llm_total_tokens: number; llm_cost_usd: number; api_requests: number }[]> =>
      request(`${BASE}/usage/history?months=${months}`),
    aiCosts: (months = 6): Promise<{ period: string; model: string; runs: number; prompt_tokens: number; completion_tokens: number; cost_usd: number }[]> =>
      request(`${BASE}/usage/ai-costs?months=${months}`),
    limits: (period?: string): Promise<{ period: string; plan: string; usage: Record<string, number>; limits: Record<string, number>; remaining: Record<string, number> }> => {
      const q = period ? `?period=${encodeURIComponent(period)}` : "";
      return request(`${BASE}/usage/limits${q}`);
    },
  },

  // Legacy — kept for backward compat with agent.py route
  agent: {
    process: (ticketId: string) =>
      request(`${BASE}/ai/tickets/${ticketId}/run`, { method: "POST" }),
    logs: (ticketId: string) => request(`${BASE}/agent/logs/${ticketId}`),
  },
};
