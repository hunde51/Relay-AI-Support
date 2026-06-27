import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Search, X, Users, Mail, Building2, ExternalLink } from "lucide-react";
import { useCustomers } from "@/lib/queries";
import type { ApiCustomer } from "@/lib/api/client";

export const Route = createFileRoute("/customers")({
  head: () => ({
    meta: [
      { title: "Customers — AI SupportOps Hub" },
      { name: "description", content: "Customer profiles and history." },
    ],
  }),
  component: CustomersPage,
});

function CustomersPage() {
  const [search, setSearch] = useState("");
  const { data: customers = [], isLoading, error } = useCustomers(search || undefined);

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1200px] mx-auto">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Customers</h1>
        <p className="text-sm text-muted-foreground">People who raise support tickets.</p>
      </header>

      <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
        <Search className="h-4 w-4 text-muted-foreground shrink-0" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          placeholder="Search customers by name or email…"
        />
        {search && (
          <button onClick={() => setSearch("")}>
            <X className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        )}
        <span className="text-xs text-muted-foreground shrink-0">{customers.length} total</span>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          Failed to load customers.
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl shimmer" />
          ))}
        </div>
      ) : customers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-muted-foreground">
          <Users className="h-8 w-8 opacity-30" />
          <p className="text-sm">{search ? "No customers match your search." : "No customers yet."}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(customers as ApiCustomer[]).map((c) => (
            <Link
              key={c.id}
              to="/customers/$id"
              params={{ id: c.id }}
              className="group rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/30"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary shrink-0">
                  <Users className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium truncate group-hover:text-primary transition-colors">{c.name}</div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                    <Mail className="h-3 w-3" />
                    <span className="truncate">{c.email}</span>
                  </div>
                  {c.company && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                      <Building2 className="h-3 w-3" />
                      <span className="truncate">{c.company}</span>
                    </div>
                  )}
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
