import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useValidateInvite, useAcceptInvitation } from "@/lib/queries";
import { useAuth } from "@/lib/auth";
import { CheckCircle, XCircle, Clock, Loader2 } from "lucide-react";

export const Route = createFileRoute("/accept-invite")({
  head: () => ({
    meta: [
      { title: "Accept Invitation — RelayAI" },
      { name: "description", content: "Set your password and join your organization." },
    ],
  }),
  component: AcceptInvitePage,
});

function AcceptInvitePage() {
  const search = Route.useSearch() as { token?: string };
  const token = search.token || "";
  const navigate = useNavigate();
  const { login } = useAuth();

  const { data: validation, isLoading: validating, error: validateError } = useValidateInvite(token);
  const acceptInvite = useAcceptInvitation();

  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [acceptError, setAcceptError] = useState<string | null>(null);

  const handleAccept = () => {
    if (!name.trim() || password.length < 6) return;
    setAcceptError(null);
    acceptInvite.mutate({ token, name: name.trim(), password }, {
      onSuccess: (data) => {
        login({
          token: data.access_token,
          userId: data.user_id,
          organizationId: data.organization_id,
          role: data.role,
        });
        navigate({ to: "/" });
      },
      onError: (err: unknown) => {
        setAcceptError(err instanceof Error ? err.message : "Failed to accept invitation");
      },
    });
  };

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md w-full text-center space-y-4">
          <XCircle className="h-12 w-12 text-destructive mx-auto" />
          <h1 className="text-xl font-semibold">Missing invitation token</h1>
          <p className="text-sm text-muted-foreground">No invitation token was provided. Check your invitation link.</p>
        </div>
      </div>
    );
  }

  if (validating) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">Validating your invitation…</p>
        </div>
      </div>
    );
  }

  if (validateError || !validation?.valid) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md w-full text-center space-y-4">
          <XCircle className="h-12 w-12 text-destructive mx-auto" />
          <h1 className="text-xl font-semibold">Invitation invalid</h1>
          <p className="text-sm text-muted-foreground">{validation?.message || "This invitation link is invalid, expired, or has already been used."}</p>
          <div className="pt-2">
            <Link to="/" className="text-sm text-primary hover:underline">Go to home</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-8">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center space-y-2">
          <CheckCircle className="h-10 w-10 text-primary mx-auto" />
          <h1 className="text-xl font-semibold">Join {validation.organization_name}</h1>
          <p className="text-sm text-muted-foreground">
            You've been invited as <strong className="capitalize">{validation.role}</strong>.
            Set your name and password to get started.
          </p>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div>
            <label className="text-sm font-medium block mb-1">Email</label>
            <p className="text-sm text-muted-foreground">{validation.email}</p>
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Role</label>
            <p className="text-sm capitalize text-muted-foreground">{validation.role}</p>
          </div>

          {validation.expires_at && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span>Expires {new Date(validation.expires_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div>
            <label className="text-sm font-medium block mb-1">Full name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Jane Smith"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              onKeyDown={(e) => { if (e.key === "Enter") handleAccept(); }}
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              onKeyDown={(e) => { if (e.key === "Enter") handleAccept(); }}
            />
          </div>

          {acceptError && (
            <p className="text-xs text-destructive">{acceptError}</p>
          )}

          <button onClick={handleAccept}
            disabled={acceptInvite.isPending || !name.trim() || password.length < 6}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50 transition-transform active:scale-[0.98]"
          >
            {acceptInvite.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {acceptInvite.isPending ? "Creating account…" : "Accept & Join"}
          </button>
        </div>
      </div>
    </div>
  );
}
