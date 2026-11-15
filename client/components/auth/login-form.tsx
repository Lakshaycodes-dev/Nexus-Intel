"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Email/password sign-in form.
 *
 * On success the token is stored by `AuthProvider.signIn` and the visitor is
 * sent to the `next` destination (or the dashboard) they originally asked for.
 */
export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const requested = searchParams.get("next");
  const destination = requested?.startsWith("/") ? requested : "/dashboard";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    setError(null);
    setPending(true);
    try {
      await signIn(email.trim(), password);
      router.replace(destination);
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Could not sign in. Check your connection and try again.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-[12px] leading-relaxed text-rose-700"
        >
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <label className="block">
        <span className="mb-1.5 block text-[11.5px] font-medium text-slate-700">
          Work email
        </span>
        <Input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@company.com"
          required
        />
      </label>

      <label className="block">
        <span className="mb-1.5 block text-[11.5px] font-medium text-slate-700">
          Password
        </span>
        <Input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Your password"
          required
        />
      </label>

      <Button
        type="submit"
        size="md"
        className="h-11 w-full"
        disabled={pending || !email.trim() || !password}
      >
        {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {pending ? "Signing in…" : "Sign in to workspace"}
        {!pending ? <ArrowRight className="h-4 w-4" /> : null}
      </Button>
    </form>
  );
}
