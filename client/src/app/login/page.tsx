'use client';

import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, Input, Navbar } from "@/components/entropy-ui";
import { login, saveAuth } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const tokens = await login(email, password);
      saveAuth({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const next = searchParams.get("next") ?? "/dashboard";
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Navbar />
      <main className="flex min-h-[calc(100vh-73px)] items-center justify-center px-6 py-10">
        <div className="w-full max-w-md rounded-md border border-zinc-800 bg-zinc-950/70 p-8">
          <p className="text-sm uppercase tracking-[0.3em] text-zinc-500">Access your workspace</p>
          <h1 className="mt-3 text-3xl font-semibold text-zinc-100">Sign in</h1>
          <p className="mt-3 text-sm leading-7 text-zinc-400">
            Use the same credentials you created in the backend to begin scanning your domains.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label className="mb-2 block text-sm text-zinc-400" htmlFor="email">
                Email
              </label>
              <Input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
            </div>
            <div>
              <label className="mb-2 block text-sm text-zinc-400" htmlFor="password">
                Password
              </label>
              <Input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" />
            </div>
            {error ? <p className="text-sm text-rose-400">{error}</p> : null}
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-zinc-400">
            New here? <Link href="/register" className="text-zinc-100">Create an account</Link>
          </p>
        </div>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black text-zinc-100" />}> 
      <LoginForm />
    </Suspense>
  );
}
