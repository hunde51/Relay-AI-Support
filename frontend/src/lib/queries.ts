import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api/client";

// ── Query keys ────────────────────────────────────────────────────────────────
export const keys = {
  dashboardSummary: ["dashboard", "summary"] as const,
  recentActivity:   ["dashboard", "recent-activity"] as const,
  ticketVolume:     ["dashboard", "ticket-volume"] as const,
  tickets:          (p?: object) => ["tickets", p ?? {}] as const,
  ticket:           (id: string) => ["ticket", id] as const,
  ticketMessages:   (id: string) => ["ticket", id, "messages"] as const,
  ticketTimeline:   (id: string) => ["ticket", id, "timeline"] as const,
  ticketActions:    (id: string) => ["ticket", id, "actions"] as const,
  kbDocuments:      ["kb", "documents"] as const,
  kbSources:        ["kb", "sources"] as const,
  kbChunks:         (id: string) => ["kb", "chunks", id] as const,
  kbSearch:         (q: string) => ["kb", "search", q] as const,
  analyticsCategories:     ["analytics", "categories"] as const,
  analyticsResolution:     ["analytics", "resolution"] as const,
  analyticsAutoRate:       ["analytics", "auto-rate"] as const,
  analyticsPeakHours:      ["analytics", "peak-hours"] as const,
  settingsWorkspace:       ["settings", "workspace"] as const,
  settingsAI:              ["settings", "ai"] as const,
  settingsNotifications:   ["settings", "notifications"] as const,
  settingsIntegrations:    ["settings", "integrations"] as const,
  customers:        (q?: string) => ["customers", q ?? ""] as const,
  customer:         (id: string) => ["customer", id] as const,
  customerTickets:  (id: string) => ["customer", id, "tickets"] as const,
  apiKeys:          ["api-keys"] as const,
  webhookEndpoints: ["webhooks", "endpoints"] as const,
  webhookDeliveries:["webhooks", "deliveries"] as const,
  widgetKeys:       ["settings", "widget"] as const,
  invitations:      ["invitations"] as const,
  members:          ["invitations", "members"] as const,
  usageSummary:     ["usage", "summary"] as const,
  usageHistory:     ["usage", "history"] as const,
  usageAICosts:     ["usage", "ai-costs"] as const,
  usageLimits:      ["usage", "limits"] as const,
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const useDashboardSummary = () =>
  useQuery({ queryKey: keys.dashboardSummary, queryFn: api.dashboard.summary });

export const useRecentActivity = () =>
  useQuery({ queryKey: keys.recentActivity, queryFn: api.dashboard.recentActivity, staleTime: 30_000 });

export const useTicketVolume = () =>
  useQuery({ queryKey: keys.ticketVolume, queryFn: api.dashboard.ticketVolume, staleTime: 60_000 });

// ── Tickets ───────────────────────────────────────────────────────────────────
export const useTicketQuery = (id: string) =>
  useQuery({ queryKey: keys.ticket(id), queryFn: () => api.tickets.get(id), staleTime: 15_000 });

export const useTicketMessages = (id: string) =>
  useQuery({ queryKey: keys.ticketMessages(id), queryFn: () => api.tickets.messages(id) });

export const useTicketTimeline = (id: string) =>
  useQuery({ queryKey: keys.ticketTimeline(id), queryFn: () => api.tickets.timeline(id) });

export const useTicketActions = (id: string) =>
  useQuery({ queryKey: keys.ticketActions(id), queryFn: () => api.ai.suggestedActions(id) });

export const useTicketAudits = (id: string) =>
  useQuery({ queryKey: ["ticket", id, "audits"], queryFn: () => api.ai.audits(id) });

export const useResolveTicket = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.tickets.resolve(id),
    onSuccess: (updated) => {
      qc.setQueryData(keys.ticket(id), updated);
      qc.invalidateQueries({ queryKey: keys.ticketTimeline(id) });
      qc.invalidateQueries({ queryKey: keys.dashboardSummary });
    },
  });
};

export const useEscalateTicket = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.tickets.escalate(id),
    onSuccess: (updated) => {
      qc.setQueryData(keys.ticket(id), updated);
      qc.invalidateQueries({ queryKey: keys.ticketTimeline(id) });
    },
  });
};

export const useSendMessage = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.tickets.addMessage(id, { body, sender_type: "agent" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ticketMessages(id) }),
  });
};

export const useRunAI = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.ai.run(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ticketActions(id) }),
  });
};

export const useApproveAction = (ticketId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => api.ai.approve(actionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ticketActions(ticketId) }),
  });
};

export const useRejectAction = (ticketId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => api.ai.reject(actionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ticketActions(ticketId) }),
  });
};

export const useExecuteAction = (ticketId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => api.ai.executeAction(actionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ticketActions(ticketId) }),
  });
};

export const useCloseTicket = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.tickets.close(id),
    onSuccess: (updated) => {
      qc.setQueryData(keys.ticket(id), updated);
      qc.invalidateQueries({ queryKey: keys.ticketTimeline(id) });
      qc.invalidateQueries({ queryKey: keys.dashboardSummary });
    },
  });
};

export const useAssignTicket = (id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (assigneeId: string) => api.tickets.assign(id, assigneeId),
    onSuccess: (updated) => {
      qc.setQueryData(keys.ticket(id), updated);
      qc.invalidateQueries({ queryKey: keys.ticketTimeline(id) });
    },
  });
};

// ── Customers ──────────────────────────────────────────────────────────────────
export const useCustomers = (search?: string) =>
  useQuery({
    queryKey: keys.customers(search),
    queryFn: () => api.customers.list(search),
  });

export const useCustomer = (id: string) =>
  useQuery({
    queryKey: keys.customer(id),
    queryFn: () => api.customers.get(id),
    enabled: Boolean(id),
  });

export const useCustomerTickets = (id: string) =>
  useQuery({
    queryKey: keys.customerTickets(id),
    queryFn: () => api.customers.getTickets(id),
    enabled: Boolean(id),
  });

// ── Knowledge ─────────────────────────────────────────────────────────────────
export const useKBDocuments = () =>
  useQuery({ queryKey: keys.kbDocuments, queryFn: () => api.knowledge.documents() });

export const useKBSources = () =>
  useQuery({ queryKey: keys.kbSources, queryFn: () => api.knowledge.sources(), staleTime: 60_000 });

export const useKBChunks = (documentId: string | null) =>
  useQuery({
    queryKey: documentId ? keys.kbChunks(documentId) : ["kb", "chunks", "none"],
    queryFn: () => api.knowledge.chunks(documentId as string),
    enabled: Boolean(documentId),
    staleTime: 60_000,
  });

export const useKBSearch = (query: string) =>
  useQuery({
    queryKey: keys.kbSearch(query),
    queryFn: () => api.knowledge.search(query),
    enabled: query.trim().length > 0,
    staleTime: 60_000,
  });

export const useIngestDocument = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.knowledge.ingest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.kbDocuments }),
  });
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const useAnalyticsCategories = () =>
  useQuery({ queryKey: keys.analyticsCategories, queryFn: api.analytics.categories, staleTime: 60_000 });

export const useAnalyticsResolution = () =>
  useQuery({ queryKey: keys.analyticsResolution, queryFn: api.analytics.resolutionTrend, staleTime: 60_000 });

export const useAnalyticsAutoRate = () =>
  useQuery({ queryKey: keys.analyticsAutoRate, queryFn: api.analytics.autoResolutionRate, staleTime: 60_000 });

export const useAnalyticsPeakHours = () =>
  useQuery({ queryKey: keys.analyticsPeakHours, queryFn: api.analytics.peakHours, staleTime: 60_000 });

// ── Settings ──────────────────────────────────────────────────────────────────
export const useWorkspaceSettings = () =>
  useQuery({ queryKey: keys.settingsWorkspace, queryFn: api.settings.workspace, staleTime: 120_000 });

export const useAISettings = () =>
  useQuery({ queryKey: keys.settingsAI, queryFn: api.settings.ai, staleTime: 120_000 });

export const useNotificationSettings = () =>
  useQuery({ queryKey: keys.settingsNotifications, queryFn: api.settings.notifications, staleTime: 120_000 });

export const usePatchWorkspace = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.patchWorkspace,
    onSuccess: (data) => qc.setQueryData(keys.settingsWorkspace, data),
  });
};

export const usePatchAISettings = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.patchAI,
    onSuccess: (data) => qc.setQueryData(keys.settingsAI, data),
  });
};

// ── API Keys ──────────────────────────────────────────────────────────────────
export const useApiKeys = () =>
  useQuery({ queryKey: keys.apiKeys, queryFn: api.apiKeys.list, staleTime: 30_000 });

export const useCreateApiKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; scopes?: string[] }) => api.apiKeys.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.apiKeys }),
  });
};

export const useRevokeApiKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.apiKeys.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.apiKeys }),
  });
};

export const useRotateApiKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.apiKeys.rotate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.apiKeys }),
  });
};

// ── Webhooks ──────────────────────────────────────────────────────────────────
export const useWebhookEndpoints = () =>
  useQuery({ queryKey: keys.webhookEndpoints, queryFn: api.webhooks.listEndpoints, staleTime: 30_000 });

export const useCreateWebhookEndpoint = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { url: string; events: string[] }) => api.webhooks.createEndpoint(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.webhookEndpoints }),
  });
};

export const useDeleteWebhookEndpoint = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.webhooks.deleteEndpoint(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.webhookEndpoints }),
  });
};

export const useWebhookDeliveries = () =>
  useQuery({ queryKey: keys.webhookDeliveries, queryFn: api.webhooks.listDeliveries, staleTime: 30_000 });

export const useTestWebhookEndpoint = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.webhooks.testEndpoint(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.webhookDeliveries }),
  });
};

// ── Widget keys ───────────────────────────────────────────────────────────────
export const useWidgetKeys = () =>
  useQuery({ queryKey: keys.widgetKeys, queryFn: api.widgetKeys.list, staleTime: 30_000 });

export const useCreateWidgetKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; allowed_origins?: string[] }) => api.widgetKeys.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.widgetKeys }),
  });
};

export const useUpdateWidgetKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; allowed_origins?: string[] } }) =>
      api.widgetKeys.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.widgetKeys }),
  });
};

export const useRevokeWidgetKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.widgetKeys.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.widgetKeys }),
  });
};

// ── Invitations ──────────────────────────────────────────────────────────────
export const useInvitations = () =>
  useQuery({ queryKey: keys.invitations, queryFn: api.invitations.list, staleTime: 30_000 });

export const useTeamMembers = () =>
  useQuery({ queryKey: keys.members, queryFn: api.invitations.members, staleTime: 30_000 });

export const useCreateInvitation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; role: string }) => api.invitations.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.invitations });
      qc.invalidateQueries({ queryKey: keys.members });
    },
  });
};

export const useRevokeInvitation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.invitations.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.invitations }),
  });
};

export const useValidateInvite = (token: string) =>
  useQuery({
    queryKey: ["invitations", "validate", token] as const,
    queryFn: () => api.invitations.validate(token),
    enabled: Boolean(token),
    retry: false,
    staleTime: 300_000,
  });

export const useAcceptInvitation = () =>
  useMutation({
    mutationFn: (data: { token: string; name: string; password: string }) => api.invitations.accept(data),
  });

// ── Usage ──────────────────────────────────────────────────────────────────
export const useUsageSummary = (period?: string) =>
  useQuery({
    queryKey: [...keys.usageSummary, period ?? ""] as const,
    queryFn: () => api.usage.summary(period),
    staleTime: 60_000,
  });

export const useUsageHistory = (months = 12) =>
  useQuery({
    queryKey: [...keys.usageHistory, months] as const,
    queryFn: () => api.usage.history(months),
    staleTime: 120_000,
  });

export const useUsageAICosts = (months = 6) =>
  useQuery({
    queryKey: [...keys.usageAICosts, months] as const,
    queryFn: () => api.usage.aiCosts(months),
    staleTime: 120_000,
  });

export const useUsageLimits = (period?: string) =>
  useQuery({
    queryKey: [...keys.usageLimits, period ?? ""] as const,
    queryFn: () => api.usage.limits(period),
    staleTime: 60_000,
  });

export const usePatchNotifications = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.patchNotifications,
    onSuccess: (data) => qc.setQueryData(keys.settingsNotifications, data),
  });
};

// ── Plan & Limits ─────────────────────────────────────────────────────────
export const usePlanSettings = () =>
  useQuery({
    queryKey: ["settings", "plan"] as const,
    queryFn: api.settings.plan,
    staleTime: 60_000,
  });

export const usePatchPlan = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.patchPlan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings", "plan"] });
      qc.invalidateQueries({ queryKey: keys.settingsWorkspace });
    },
  });
};
