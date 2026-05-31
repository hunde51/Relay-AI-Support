import { useEffect, useState } from "react";
import { api, type ApiTicket } from "@/lib/api/client";

// Simple in-memory cache so navigating back doesn't re-fetch
let cache: ApiTicket[] | null = null;

export function useTickets() {
  const [tickets, setTickets] = useState<ApiTicket[]>(cache ?? []);
  const [loading, setLoading] = useState(!cache);
  const [error, setError] = useState<string | null>(null);

  const fetch = () => {
    setLoading(true);
    setError(null);
    api.tickets.list()
      .then((data) => { cache = data; setTickets(data); })
      .catch(() => setError("Failed to load tickets. Check the backend is running."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  return { tickets, loading, error, refetch: fetch };
}
