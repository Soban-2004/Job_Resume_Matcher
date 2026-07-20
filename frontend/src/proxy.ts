import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PROTECTED_ROUTES = ["/job-seeker", "/recruiter"];
const AUTH_ROUTES = ["/login", "/signup"];

function dashboardPathFor(role: string | undefined): string {
  return role === "recruiter" ? "/recruiter" : "/job-seeker";
}

// Next.js 16 renamed Middleware to Proxy (same mechanism, new name/file) --
// this is the optimistic auth check the framework's own auth guide
// recommends: read the session, redirect if missing, never do slow/DB work
// here since Proxy runs on every route including prefetches.
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet, headers) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
          Object.entries(headers).forEach(([key, value]) => response.headers.set(key, value));
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const isProtected = PROTECTED_ROUTES.some((p) => path.startsWith(p));
  const isAuthRoute = AUTH_ROUTES.includes(path);

  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  if (isAuthRoute && user) {
    const url = request.nextUrl.clone();
    url.pathname = dashboardPathFor(user.user_metadata?.role);
    return NextResponse.redirect(url);
  }

  // One account, one mode: a job seeker can't wander into the recruiter
  // workspace and vice versa -- always bounced back to their own dashboard.
  // The home page itself is left alone even when logged in: the flow is
  // always home -> pick a mode -> log in (if needed) -> that mode's
  // dashboard, never an automatic skip past the mode picker.
  if (user) {
    const ownDashboard = dashboardPathFor(user.user_metadata?.role);
    const otherDashboard = ownDashboard === "/recruiter" ? "/job-seeker" : "/recruiter";
    if (path.startsWith(otherDashboard)) {
      const url = request.nextUrl.clone();
      url.pathname = ownDashboard;
      return NextResponse.redirect(url);
    }
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
