import { createFileRoute } from "@tanstack/react-router";
import { BookOpen, Search, Upload, RefreshCw, X } from "lucide-react";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useKBDocuments, useKBSearch, useIngestDocument, keys } from "@/lib/queries";

export const Route = createFileRoute("/knowledge-base")({
  head: () => ({
    meta: [
      { title: "Knowledge Base — AI SupportOps Hub" },
      { name: "description", content: "Articles and runbooks used by AI and human agents." },
    ],
  }),
  component: KB,
});

type KBDoc = { id: string; title: string; content_type: string; status: string; created_at: string };
type SearchResult = { chunk_id: string; source: string; content: string; score: number };

function KB() {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [committed, setCommitted] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: docs = [], isLoading } = useKBDocuments();
  const { data: searchData, isFetching: searching } = useKBSearch(committed);
  const ingest = useIngestDocument();

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/knowledge/documents/upload`, {
      method: "POST", body: form,
    }).catch(() => null);
    qc.invalidateQueries({ queryKey: keys.kbDocuments });
    e.target.value = "";
  };

  const results = committed ? (searchData?.results as SearchResult[] | undefined) ?? [] : null;

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1200px] mx-auto">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge base</h1>
          <p className="text-sm text-muted-foreground">Source of truth for AI retrieval and agent answers.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => qc.invalidateQueries({ queryKey: keys.kbDocuments })}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-accent" title="Refresh">
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
            <Upload className="h-4 w-4" /> Upload
          </button>
          <input ref={fileRef} type="file" accept=".txt,.md,.pdf" className="hidden" onChange={upload} />
        </div>
      </header>

      <div className="flex items-center gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setCommitted(query)}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            placeholder="Search knowledge base…" />
          {query && (
            <button onClick={() => { setQuery(""); setCommitted(""); }}>
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
        </div>
        <button onClick={() => setCommitted(query)} disabled={searching}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
          {searching ? "…" : "Search"}
        </button>
      </div>

      {results !== null ? (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">{results.length} result{results.length !== 1 ? "s" : ""} for "{committed}"</div>
          {results.length === 0 && <p className="text-sm text-muted-foreground">No matching chunks found.</p>}
          {results.map((r) => (
            <div key={r.chunk_id} className="rounded-xl border border-border bg-card p-4 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{r.source}</span>
                <span className="font-mono">score {r.score?.toFixed(3)}</span>
              </div>
              <p className="text-sm leading-relaxed line-clamp-3">{r.content}</p>
            </div>
          ))}
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-20 rounded-xl shimmer" />)}
        </div>
      ) : (docs as KBDoc[]).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-muted-foreground">
          <BookOpen className="h-8 w-8 opacity-30" />
          <p className="text-sm">No documents yet. Upload a file to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(docs as KBDoc[]).map((d) => (
            <div key={d.id} className="group rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/30">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                  <BookOpen className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium truncate">{d.title}</div>
                  <div className="text-xs text-muted-foreground">{d.content_type} · {d.status}</div>
                </div>
                {d.status !== "ingested" && (
                  <button onClick={() => ingest.mutate(d.id)} disabled={ingest.isPending}
                    className="shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50">
                    {ingest.isPending ? "…" : "Ingest"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
