import { createFileRoute } from "@tanstack/react-router";
import { BookOpen, Search, Upload, RefreshCw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";

export const Route = createFileRoute("/knowledge-base")({
  head: () => ({
    meta: [
      { title: "Knowledge Base — AI SupportOps Hub" },
      { name: "description", content: "Articles and runbooks used by AI and human agents." },
    ],
  }),
  component: KB,
});

type KBDoc = { id: string; title: string; content_type: string; status: string; source_id: string; created_at: string };
type SearchResult = { chunk_id: string; document_id: string; source: string; content: string; score: number };

function KB() {
  const [docs, setDocs] = useState<KBDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [ingesting, setIngesting] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => {
    setLoading(true);
    api.knowledge.documents()
      .then((d) => setDocs(d as KBDoc[]))
      .catch(() => null)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/knowledge/documents/upload`, {
      method: "POST", body: form,
    }).catch(() => null);
    load();
    e.target.value = "";
  };

  const ingest = async (id: string) => {
    setIngesting(id);
    await api.knowledge.ingest(id).catch(() => null);
    setIngesting(null);
    load();
  };

  const search = async () => {
    if (!query.trim()) { setResults(null); return; }
    setSearching(true);
    const res = await api.knowledge.search(query).catch(() => null);
    setResults((res?.results as SearchResult[]) ?? []);
    setSearching(false);
  };

  return (
    <div className="px-4 md:px-8 py-6 md:py-8 space-y-6 max-w-[1200px] mx-auto">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge base</h1>
          <p className="text-sm text-muted-foreground">Source of truth for AI retrieval and agent answers.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-accent" title="Refresh">
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
            <Upload className="h-4 w-4" /> Upload
          </button>
          <input ref={fileRef} type="file" accept=".txt,.md,.pdf" className="hidden" onChange={upload} />
        </div>
      </header>

      {/* Search */}
      <div className="flex items-center gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            placeholder="Search knowledge base…" />
          {query && <button onClick={() => { setQuery(""); setResults(null); }}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>}
        </div>
        <button onClick={search} disabled={searching}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
          {searching ? "…" : "Search"}
        </button>
      </div>

      {/* Search results */}
      {results !== null && (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">{results.length} result{results.length !== 1 ? "s" : ""} for "{query}"</div>
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
      )}

      {/* Documents */}
      {results === null && (
        <>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-20 rounded-xl shimmer" />)}
            </div>
          ) : docs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 gap-2 text-muted-foreground">
              <BookOpen className="h-8 w-8 opacity-30" />
              <p className="text-sm">No documents yet. Upload a file to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {docs.map((d) => (
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
                      <button onClick={() => ingest(d.id)} disabled={ingesting === d.id}
                        className="shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50">
                        {ingesting === d.id ? "…" : "Ingest"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
