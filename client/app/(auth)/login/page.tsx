import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to your Nexus-Intel workspace.",
};

export default function LoginPage() {
  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your Nexus-Intel workspace to pick up where you left off."
      footer={
        <span>
          New to Nexus-Intel?{" "}
          <Link
            href="/signup"
            className="font-semibold text-indigo-600 transition hover:text-indigo-700"
          >
            Create an account
          </Link>
        </span>
      }
    >
      <Suspense
        fallback={<div className="h-[212px] animate-pulse rounded-xl bg-slate-100" />}
      >
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
