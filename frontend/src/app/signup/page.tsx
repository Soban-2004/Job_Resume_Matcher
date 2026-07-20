"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Briefcase, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { createClient } from "@/lib/supabase/client";
import { GRADIENT_CTA } from "@/lib/category-theme";
import { cn } from "@/lib/utils";

type Role = "job_seeker" | "recruiter";

export default function SignupPage() {
  const [role, setRole] = useState<Role>("job_seeker");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkEmail, setCheckEmail] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const supabase = createClient();
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { role } },
      });
      if (signUpError) throw signUpError;

      if (data.session) {
        router.push(role === "recruiter" ? "/recruiter" : "/job-seeker");
        router.refresh();
      } else {
        // Email confirmation is enabled on this Supabase project -- no
        // session yet until the user clicks the link in their inbox.
        setCheckEmail(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign up.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-4 py-16">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Create your account</h1>
        <p className="text-sm text-muted-foreground">Choose how you&apos;ll use the platform.</p>
      </div>

      {checkEmail ? (
        <Alert>
          <AlertDescription>
            Check <span className="font-medium text-foreground">{email}</span> for a confirmation link
            to finish creating your account.
          </AlertDescription>
        </Alert>
      ) : (
        <Card className="flex flex-col gap-5 p-6">
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRole("job_seeker")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors",
                role === "job_seeker" ? "border-primary/50 bg-primary/5 text-foreground" : "border-border text-muted-foreground"
              )}
            >
              <Briefcase className="size-5" />
              Job Seeker
            </button>
            <button
              type="button"
              onClick={() => setRole("recruiter")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors",
                role === "recruiter" ? "border-primary/50 bg-primary/5 text-foreground" : "border-border text-muted-foreground"
              )}
            >
              <Users className="size-5" />
              Recruiter
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" className={GRADIENT_CTA} disabled={submitting}>
              {submitting ? "Creating account..." : "Sign up"}
            </Button>
          </form>
        </Card>
      )}

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
