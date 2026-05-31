import { useEffect, useState } from "react";
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
  const [tickets, setTickets] = useState<ApiTicket[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = () => {
    setLoading(true);
    setError(null);
    api.tickets
      .list(filters)
      .then((data) => {
        setTickets(data.items);
        setTotal(data.total);
        setPages(data.pages);
      })
      .catch(() => setError("Failed to load tickets. Check the backend is running."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters?.status, filters?.priority, filters?.category, filters?.search, filters?.page]);

  return { tickets, total, pages, loading, error, refetch: fetch };
}
