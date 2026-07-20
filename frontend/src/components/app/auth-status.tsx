"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

export function AuthStatus() {
  const [email, setEmail] = useState<string | null | undefined>(undefined);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();

    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user?.email ?? null);
    });

    return () => subscription.subscription.unsubscribe();
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  // undefined = not yet checked (avoid a flash of the wrong state)
  if (email === undefined) return null;

  if (email === null) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <Link href="/login" className="text-muted-foreground hover:text-foreground">
          Log in
        </Link>
        <Link href="/signup" className="font-medium text-primary hover:underline">
          Sign up
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="hidden text-muted-foreground sm:inline">{email}</span>
      <Button variant="ghost" size="sm" className="gap-1.5" onClick={handleLogout}>
        <LogOut className="size-3.5" />
        Log out
      </Button>
    </div>
  );
}
