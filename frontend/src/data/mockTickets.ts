export type TicketStatus = "open" | "in_progress" | "resolved";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketCategory = "billing" | "bug" | "general" | "account" | "feature";

export interface Ticket {
  id: string;
  customer: string;
  email: string;
  subject: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  createdAt: string;
  updatedAt: string;
  assignee?: string;
  messages: { from: "customer" | "agent" | "ai"; body: string; at: string }[];
}

const now = Date.now();
const min = (m: number) => new Date(now - m * 60_000).toISOString();

export const tickets: Ticket[] = [
  {
    id: "TKT-1023",
    customer: "Amelia Hart",
    email: "amelia@northwind.co",
    subject: "Invoice charged twice for May",
    category: "billing",
    priority: "high",
    status: "open",
    createdAt: min(8),
    updatedAt: min(2),
    messages: [
      { from: "customer", body: "Hi — I was charged twice for the May invoice. Please refund the duplicate.", at: min(8) },
      { from: "ai", body: "Detected duplicate Stripe charge ch_3Pq...x. Refund eligible.", at: min(6) },
    ],
  },
  {
    id: "TKT-1022",
    customer: "Marcus Lee",
    email: "marcus@finch.io",
    subject: "Webhook delivery failing with 502",
    category: "bug",
    priority: "urgent",
    status: "in_progress",
    createdAt: min(22),
    updatedAt: min(4),
    assignee: "Priya N.",
    messages: [
      { from: "customer", body: "Our webhook endpoint is returning 502s since 14:00 UTC.", at: min(22) },
      { from: "agent", body: "Looking into the edge routing now.", at: min(15) },
    ],
  },
  {
    id: "TKT-1021",
    customer: "Sofia Bianchi",
    email: "sofia@lumen.studio",
    subject: "How do I invite teammates?",
    category: "general",
    priority: "low",
    status: "resolved",
    createdAt: min(95),
    updatedAt: min(40),
    messages: [
      { from: "customer", body: "Where do I add users to my workspace?", at: min(95) },
      { from: "ai", body: "Settings → Team → Invite. Sent the guide link.", at: min(90) },
    ],
  },
  {
    id: "TKT-1020",
    customer: "Daniel Okoye",
    email: "daniel@kestrel.dev",
    subject: "SSO with Okta returns invalid_grant",
    category: "account",
    priority: "high",
    status: "open",
    createdAt: min(120),
    updatedAt: min(18),
    messages: [
      { from: "customer", body: "SSO suddenly stopped working for our org.", at: min(120) },
    ],
  },
  {
    id: "TKT-1019",
    customer: "Yuki Tanaka",
    email: "yuki@maru.jp",
    subject: "Feature request: bulk export CSV",
    category: "feature",
    priority: "medium",
    status: "in_progress",
    createdAt: min(240),
    updatedAt: min(60),
    assignee: "Jordan K.",
    messages: [
      { from: "customer", body: "Would love a bulk CSV export across workspaces.", at: min(240) },
    ],
  },
  {
    id: "TKT-1018",
    customer: "Elena Ruiz",
    email: "elena@vela.mx",
    subject: "Reset 2FA after lost device",
    category: "account",
    priority: "medium",
    status: "resolved",
    createdAt: min(360),
    updatedAt: min(300),
    messages: [
      { from: "customer", body: "Lost phone — need 2FA reset.", at: min(360) },
      { from: "agent", body: "Identity confirmed. 2FA reset.", at: min(305) },
    ],
  },
  {
    id: "TKT-1017",
    customer: "Henrik Sørensen",
    email: "henrik@fjord.no",
    subject: "Latency spike on EU region",
    category: "bug",
    priority: "high",
    status: "open",
    createdAt: min(45),
    updatedAt: min(12),
    messages: [
      { from: "customer", body: "Seeing p95 ~ 1.8s in eu-west-1.", at: min(45) },
    ],
  },
  {
    id: "TKT-1016",
    customer: "Priya Nair",
    email: "priya@indra.in",
    subject: "Annual plan discount inquiry",
    category: "billing",
    priority: "low",
    status: "in_progress",
    createdAt: min(180),
    updatedAt: min(70),
    messages: [
      { from: "customer", body: "Do you offer annual billing discounts?", at: min(180) },
    ],
  },
];

export function getTicket(id: string) {
  return tickets.find((t) => t.id === id);
}
