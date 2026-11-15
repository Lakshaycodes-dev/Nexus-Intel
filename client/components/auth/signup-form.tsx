"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const MIN_PASSWORD_LENGTH = 8;

/**
 * Account creation form.
 *
 * The workspace name is optional: the API derives "<first name>'s workspace"
 * when it is left blank, which keeps onboarding to a single screen.
 */
export function SignupForm() {
  const router = useRouter();
  const { signUp } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function validate(): string | null {
    if (!name.trim()) return "Tell us your name so we can personalise the workspace.";
    if (!email.trim()) return "Enter the email you want to sign in with.";
    if (password.length < MIN_PASSWORD_LENGTH) {
      return `Use at least ${MIN_PASSWORD_LENGTH} characters for your password.`;
    }
    if (password !== confirm) return "The two passwords do not match.";
    return null;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }

    setError(null);
    setPending(true);
    try {
      await signUp({
        name: name.trim(),
        email: email.trim(),
        password,
        workspace_name: workspace.trim() || undefined,
      });
      router.replace("/dashboard");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Could not create your account. Check your connection and try again.",
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
          Full name
        </span>
        <Input
          autoComplete="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Lakshay Sharma"
          required
        />
      </label>

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
          Workspace name <span className="font-normal text-slate-400">(optional)</span>
        </span>
        <Input
          autoComplete="organization"
          value={workspace}
          onChange={(event) => setWorkspace(event.target.value)}
          placeholder="Lakshay Retail"
        />
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1.5 block text-[11.5px] font-medium text-slate-700">
            Password
          </span>
          <Input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={`${MIN_PASSWORD_LENGTH}+ characters`}
            required
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-[11.5px] font-medium text-slate-700">
            Confirm password
          </span>
          <Input
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            placeholder="Repeat password"
            required
          />
        </label>
      </div>

      <Button
        type="submit"
        size="md"
        className="h-11 w-full"
        disabled={pending}
      >
        {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {pending ? "Creating your workspace…" : "Create account"}
        {!pending ? <ArrowRight className="h-4 w-4" /> : null}
      </Button>
    </form>
  );
}
