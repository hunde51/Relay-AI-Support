export type AIStepKind = "triage" | "rag" | "decision" | "action";

export interface AIStep {
  id: string;
  kind: AIStepKind;
  agent: string;
  title: string;
  summary: string;
  reasoning: string;
  confidence: number; // 0..1
  ticketId: string;
  at: string;
  snippets?: { title: string; source: string; excerpt: string }[];
}

const now = Date.now();
const ago = (s: number) => new Date(now - s * 1000).toISOString();

export const aiActivity: AIStep[] = [
  {
    id: "a1",
    kind: "triage",
    agent: "Triage Agent",
    title: "Billing issue detected",
    summary: "Classified TKT-1023 as duplicate-charge / billing.",
    reasoning:
      "Customer mentions 'charged twice' and 'May invoice'. Stripe metadata shows two charges within 12s. Routed to Billing queue.",
    confidence: 0.94,
    ticketId: "TKT-1023",
    at: ago(8),
  },
  {
    id: "a2",
    kind: "rag",
    agent: "Knowledge Agent",
    title: "Found 3 relevant documents",
    summary: "Retrieved refund policy + duplicate-charge runbook.",
    reasoning:
      "Top-k retrieval over support KB. Documents matched on 'duplicate charge', 'refund window', 'Stripe webhook idempotency'.",
    confidence: 0.88,
    ticketId: "TKT-1023",
    at: ago(20),
    snippets: [
      { title: "Refund policy — duplicate charges", source: "kb/billing/refunds.md", excerpt: "Duplicate charges within 24h are auto-eligible for refund without manager approval." },
      { title: "Stripe idempotency keys", source: "kb/eng/stripe.md", excerpt: "Use idempotency_key on POST /charges to prevent client retries from double-billing." },
      { title: "Refund SLA", source: "kb/policy/sla.md", excerpt: "Refunds appear on customer statements within 5–10 business days." },
    ],
  },
  {
    id: "a3",
    kind: "decision",
    agent: "Decision Agent",
    title: "Auto-resolve recommended",
    summary: "Proposes issuing refund for duplicate Stripe charge.",
    reasoning:
      "Policy allows auto-refund < $500 within 24h with confidence ≥ 0.85. Charge is $129, both criteria met.",
    confidence: 0.91,
    ticketId: "TKT-1023",
    at: ago(38),
  },
  {
    id: "a4",
    kind: "action",
    agent: "Action Agent",
    title: "Drafted customer reply",
    summary: "Reply pending agent review before send.",
    reasoning:
      "Generated empathetic reply confirming refund, ETA, and reference number. Awaiting human approval.",
    confidence: 0.86,
    ticketId: "TKT-1023",
    at: ago(54),
  },
  {
    id: "a5",
    kind: "triage",
    agent: "Triage Agent",
    title: "Webhook outage flagged",
    summary: "TKT-1022 escalated to on-call.",
    reasoning:
      "Pattern match against incident heuristics: 502 + webhook + multiple customers in 10min window → P1.",
    confidence: 0.97,
    ticketId: "TKT-1022",
    at: ago(120),
  },
];
