'use client';

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Input, Navbar } from "@/components/entropy-ui";
import { register, saveAuth } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      await register(email, password, fullName || undefined);
      const tokens = await (await import("@/lib/api")).login(email, password);
      saveAuth({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Navbar />
      <main className="flex min-h-[calc(100vh-73px)] items-center justify-center px-6 py-10">
        <div className="w-full max-w-md rounded-md border border-zinc-800 bg-zinc-950/70 p-8">
          <p className="text-sm uppercase tracking-[0.3em] text-zinc-500">Create an account</p>
          <h1 className="mt-3 text-3xl font-semibold text-zinc-100">Register</h1>
          <p className="mt-3 text-sm leading-7 text-zinc-400">
            Sign up to orchestrate security scans from a minimal dark workspace built for fast demos.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label className="mb-2 block text-sm text-zinc-400" htmlFor="name">
                Full name
              </label>
              <Input id="name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Alex Chen" />
            </div>
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
              {busy ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-zinc-400">
            Already have an account? <Link href="/login" className="text-zinc-100">Sign in</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
