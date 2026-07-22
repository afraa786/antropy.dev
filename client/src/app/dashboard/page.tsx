'use client';

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Input, Navbar, ScanRow } from "@/components/entropy-ui";
import { clearAuth, getActiveOrgId, getAuthToken, getMe, getOrganizations, listScanJobs, quickScan, setActiveOrgId } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Array<{ id: string; domain_id: string; status: string; created_at: string; scan_type: string }>>([]);
  const [orgId, setOrgId] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuthToken()) {
      router.replace("/login?next=/dashboard");
      return;
    }

    const load = async () => {
      try {
        const me = await getMe();
        if (!me?.email) {
          clearAuth();
          router.replace("/login?next=/dashboard");
          return;
        }

        const organizations = await getOrganizations();
        const firstOrg = organizations[0];
        if (!firstOrg) {
          setLoading(false);
          return;
        }
        setActiveOrgId(firstOrg.id);
        setOrgId(firstOrg.id);
        const scanJobs = await listScanJobs(firstOrg.id);
        setJobs(scanJobs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load dashboard");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [router]);

  const handleScan = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!domain.trim()) return;
    setBusy(true);
    setError(null);

    try {
      const response = await quickScan(domain.trim());
      router.push(`/scan/${response.scan_job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start scan");
    } finally {
      setBusy(false);
    }
  };

  const activeOrgId = useMemo(() => orgId ?? getActiveOrgId(), [orgId]);

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Navbar />
      <main className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-10 lg:px-8">
        <section className="flex flex-col gap-6 border-b border-zinc-800 pb-8 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-zinc-500">Workspace overview</p>
            <h1 className="mt-3 text-3xl font-semibold text-zinc-100 sm:text-4xl">
              Continuous defense, one scan away.
            </h1>
          </div>
          <form onSubmit={handleScan} className="flex w-full flex-col gap-3 md:w-[420px] md:flex-row">
            <Input
              placeholder="Enter your domain"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
            />
            <Button type="submit" disabled={busy} className="min-w-[140px]">
              {busy ? "Starting..." : "New Scan"}
            </Button>
          </form>
        </section>

        {error ? <p className="rounded-md border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-300">{error}</p> : null}

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-zinc-500">Recent scans</p>
              <h2 className="mt-2 text-xl font-semibold text-zinc-100">Your scan history</h2>
            </div>
            <Link href="/" className="text-sm text-zinc-400 transition hover:text-zinc-100">
              Back home
            </Link>
          </div>

          {loading ? (
            <p className="text-sm text-zinc-400">Loading scan history…</p>
          ) : jobs.length === 0 ? (
            <p className="rounded-md border border-zinc-800 px-4 py-6 text-sm text-zinc-400">
              No scans yet. Start a new one from the top bar.
            </p>
          ) : (
            <div className="rounded-md border border-zinc-800 bg-zinc-950/70 px-4">
              {jobs.map((job) => (
                <ScanRow
                  key={job.id}
                  title={job.domain_id}
                  status={job.status}
                  timestamp={new Date(job.created_at).toLocaleString()}
                  onClick={() => router.push(`/scan/${job.id}`)}
                />
              ))}
            </div>
          )}
        </section>

        <section className="rounded-md border border-zinc-800 p-5">
          <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Active workspace</p>
          <p className="mt-2 text-sm text-zinc-400">
            {activeOrgId ? `Organization ID: ${activeOrgId}` : "No organization linked yet."}
          </p>
        </section>
      </main>
    </div>
  );
}
