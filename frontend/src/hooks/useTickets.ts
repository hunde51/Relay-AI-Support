import { useQuery } from "@tanstack/react-query";
import { api, type ApiTicket, type TicketCategory, type TicketPriority, type TicketStatus } from "@/lib/api/client";

export type TicketFilters = {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
  search?: string;
  page?: number;
  page_size?: number;
};

export function useTickets(filters?: TicketFilters) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["tickets", filters ?? {}],
    queryFn: () => api.tickets.list(filters),
    staleTime: 15_000,
  });

  return {
    tickets: data?.items ?? [] as ApiTicket[],
    total: data?.total ?? 0,
    pages: data?.pages ?? 0,
    loading: isLoading,
    error: error ? (error as Error).message : null,
    refetch: () => refetch(),
  };
}
