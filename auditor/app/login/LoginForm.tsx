"use client";

import { useActionState } from "react";
import {
  requestMagicLink,
  type RequestMagicLinkState,
} from "@/lib/auth-actions";

export default function LoginForm({ initialError }: { initialError?: string }) {
  const initialState: RequestMagicLinkState = { error: initialError };
  const [state, formAction, isPending] = useActionState(
    requestMagicLink,
    initialState
  );

  if (state.sent) {
    return (
      <main className="login-shell">
        <div className="login-card">
          <h1>Eli7 Auditor</h1>
          <p className="subtitle">
            Enviámos-te um link de acesso para o teu email. Abre-o neste
            dispositivo para entrares.
          </p>
          <button
            type="button"
            className="link-button"
            onClick={() => window.location.reload()}
          >
            Use a different email
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="login-shell">
      <form action={formAction} className="login-card">
        <h1>Eli7 Auditor</h1>
        <p className="subtitle">DianasNuvem monitoring — parent access only</p>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
        />

        {state?.error && (
          <p className="error" role="alert">
            {state.error}
          </p>
        )}

        <button type="submit" className="btn btn-primary" disabled={isPending}>
          {isPending ? "Sending…" : "Send magic link"}
        </button>
      </form>
    </main>
  );
}
