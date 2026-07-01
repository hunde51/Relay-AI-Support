import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, Mail, Building2, Ticket, Calendar, ExternalLink } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import { useCustomer, useCustomerTickets } from "@/lib/queries";
import { StatusBadge, PriorityBadge, CategoryBadge } from "@/components/tickets/Badges";

export const Route = createFileRoute("/customers/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `${params.id} — Customer` },
      { name: "description", content: "Customer profile and ticket history." },
    ],
  }),
  loader: async ({ params }) => {
    try {
      return await api.customers.get(params.id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
  },
  notFoundComponent: () => (
    <div className="px-8 py-16 text-center">
      <p className="text-sm text-muted-foreground">Customer not found.</p>
      <Link to="/customers" className="text-sm text-primary">Back to customers</Link>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="px-8 py-16 text-center text-sm text-destructive">{error.message}</div>
  ),
  component: CustomerDetail,
});

function CustomerDetail() {
  const initial = Route.useLoaderData() as { id: string };
  const { data: customer, isLoading } = useCustomer(initial.id);
  const { data: tickets = [], isLoading: ticketsLoading } = useCustomerTickets(initial.id);

  if (isLoading || !customer) {
    return (
      <div className="px-3 md:px-8 py-8 md:py-16 space-y-4 max-w-[900px] mx-auto">
        <div className="h-6 w-48 rounded shimmer" />
        <div className="h-40 rounded-xl shimmer" />
      </div>
    );
  }

  return (
    <div className="px-3 md:px-8 py-4 md:py-8 max-w-[900px] mx-auto overflow-x-hidden">
      <Link to="/customers" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3 md:mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to customers
      </Link>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }} className="rounded-xl border border-border bg-card p-4 md:p-6 space-y-4">
        <div className="flex items-start gap-3 md:gap-4">
          <div className="flex h-12 w-12 md:h-14 md:w-14 items-center justify-center rounded-full bg-primary/10 text-primary text-base md:text-lg font-semibold shrink-0">
            {customer.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <h1 className="text-lg md:text-xl font-semibold tracking-tight">{customer.name}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{customer.email}</span>
              {customer.company && <span className="flex items-center gap-1"><Building2 className="h-3 w-3" />{customer.company}</span>}
              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />Joined {new Date(customer.created_at).toLocaleDateString()}</span>
            </div>
            {customer.external_id && (
              <div className="mt-2 text-xs font-mono text-muted-foreground">External ID: {customer.external_id}</div>
            )}
          </div>
        </div>
      </motion.div>

      <div className="mt-6">
        <div className="flex items-center gap-2 mb-3">
          <Ticket className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Ticket history</h2>
        </div>

        {ticketsLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 rounded-xl shimmer" />)}
          </div>
        ) : tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-2 text-muted-foreground">
            <Ticket className="h-8 w-8 opacity-30" />
            <p className="text-sm">No tickets yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-border rounded-xl border border-border bg-card overflow-hidden">
            {(tickets as Array<{ id: string; title: string; status: string; priority: string; category: string; created_at: string }>).map((t) => (
              <Link key={t.id} to="/tickets/$id" params={{ id: t.id }}
                className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 px-4 md:px-5 py-3 text-sm hover:bg-accent/40 transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="font-medium truncate">{t.title}</div>
                  <div className="text-xs text-muted-foreground">{new Date(t.created_at).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap shrink-0">
                  <CategoryBadge category={t.category as any} />
                  <PriorityBadge priority={t.priority as any} />
                  <StatusBadge status={t.status as any} />
                </div>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 hidden sm:block" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
