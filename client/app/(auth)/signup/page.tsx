import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = {
  title: "Create your account",
  description: "Create a Nexus-Intel workspace and start tracking your market.",
};

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your workspace"
      subtitle="Set up an account to track competitors, price movements and festive offers."
      footer={
        <span>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-indigo-600 transition hover:text-indigo-700"
          >
            Sign in
          </Link>
        </span>
      }
    >
      <SignupForm />
    </AuthShell>
  );
}
