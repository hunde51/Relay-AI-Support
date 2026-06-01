import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api/client";

// ── Query keys ────────────────────────────────────────────────────────────────
export const keys = {
  dashboardSummary: ["dashboard", "summary"] as const,
  recentActivity:   ["dashboard", "recent-activity"] as const,
  tickets:          (p?: object) => ["tickets", p ?? {}] as const,
  ticket:           (id: string) => ["ticket", id] as const,
  ticketMessages:   (id: string) => ["ticket", id, "messages"] as const,
  ticketTimeline:   (id: string) => ["ticket", id, "timeline"] as const,
  ticketActions:    (id: string) => ["ticket", id, "actions"] as const,
  customers:        (q?: string) => ["customers", q ?? ""] as const,
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
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const useDashboardSummary = () =>
  useQuery({ queryKey: keys.dashboardSummary, queryFn: api.dashboard.summary });

// ── Tickets ───────────────────────────────────────────────────────────────────
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

export const usePatchNotifications = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.patchNotifications,
    onSuccess: (data) => qc.setQueryData(keys.settingsNotifications, data),
  });
};
