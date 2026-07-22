'use client';

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button, Navbar, SeverityBadge } from "@/components/entropy-ui";
import { getActiveOrgId, getAuthToken, getDomain, getScanJob, getScanResults, clearAuth } from "@/lib/api";

type FindingItem = {
  title: string;
  description: string;
  severity: string;
};

export default function ScanPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState<null | {
    id: string;
    domain_id: string;
    status: string;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    scan_type: string;
  }>(null);
  const [domain, setDomain] = useState<string | null>(null);
  const [results, setResults] = useState<Array<{ id: string; summary: Record<string, unknown>; severity_counts: Record<string, number>; created_at: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuthToken()) {
      router.replace(`/login?next=/scan/${params.id}`);
      return;
    }

    const orgId = getActiveOrgId();
    if (!orgId) {
      router.replace("/dashboard");
      return;
    }

    let mounted = true;
    const load = async () => {
      try {
        const [scanJob, domainResponse, scanResults] = await Promise.all([
          getScanJob(params.id, orgId),
          getDomain("", orgId).catch(() => null),
          getScanResults(params.id, orgId),
        ]);

        if (!mounted) return;

        setJob(scanJob);
        setResults(scanResults);
        setDomain((domainResponse as { hostname?: string } | null | undefined)?.hostname ?? scanJob.domain_id);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Unable to load scan results");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();

    if (job?.status === "running" || job?.status === "pending") {
      const timer = window.setTimeout(() => load(), 5000);
      return () => window.clearTimeout(timer);
    }

    return () => {
      mounted = false;
    };
  }, [job?.status, params.id, router]);

  const findings = useMemo(() => {
    const collected: FindingItem[] = [];
    results.forEach((result) => {
      const summary = result.summary as Record<string, unknown>;
      const rawFindings = summary.findings;
      if (Array.isArray(rawFindings)) {
        rawFindings.forEach((item) => {
          const finding = item as Record<string, unknown>;
          collected.push({
            title: String(finding.title ?? "Finding discovered"),
            description: String(finding.description ?? "Details are available from the scan engine."),
            severity: String(finding.severity ?? "info"),
          });
        });
      } else if (typeof summary.total_findings === "number" && summary.total_findings > 0) {
        collected.push({
          title: "Scan findings detected",
          description: `The scan returned ${summary.total_findings} finding(s). Open the raw summary to inspect the details.`,
          severity: "info",
        });
      }
    });

    return collected;
  }, [results]);

  const screenshot = useMemo(() => {
    for (const result of results) {
      const allFindings = (result.summary.findings as Array<Record<string, unknown>> | undefined) ?? [];
      for (const finding of allFindings) {
        const metadata = (finding.metadata as Record<string, unknown> | undefined) ?? {};
        const screenshotUrl = metadata.screenshotURL;
        if (typeof screenshotUrl === "string" && screenshotUrl) {
          return screenshotUrl;
        }
      }
    }
    return null;
  }, [results]);

  const aiSummary = useMemo(() => {
    const summary = results[0]?.summary as Record<string, unknown> | undefined;
    return typeof summary?.ai_summary === "string" ? summary.ai_summary : "The scan has completed and is ready for review.";
  }, [results]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-zinc-100">
        <Navbar />
        <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-16 lg:px-8">
          <div className="rounded-md border border-zinc-800 bg-zinc-950/70 p-8 text-sm text-zinc-400">
            Loading scan details…
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Navbar />
      <main className="mx-auto grid max-w-7xl gap-8 px-6 py-10 lg:grid-cols-[2fr_1fr] lg:px-8">
        <div className="space-y-8">
          <section className="space-y-3">
            <p className="text-sm uppercase tracking-[0.3em] text-zinc-500">Scan report</p>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-semibold text-zinc-100">{domain ?? job?.domain_id ?? "Scan"}</h1>
              <span className="rounded-full border border-zinc-800 px-3 py-1 text-sm text-zinc-400">
                {job?.status ?? "unknown"}
              </span>
            </div>
            <p className="text-sm text-zinc-400">
              {job?.created_at ? new Date(job.created_at).toLocaleString() : "Scan started soon after submission"}
            </p>
          </section>

          <section className="rounded-md border border-zinc-800 bg-zinc-950/70 p-6">
            <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Executive summary</p>
            <p className="mt-4 text-lg leading-8 text-zinc-200">{aiSummary}</p>
          </section>

          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-zinc-100">Findings</h2>
              <Button variant="ghost" onClick={() => router.push("/dashboard")}>Back to dashboard</Button>
            </div>
            {findings.length === 0 ? (
              <p className="rounded-md border border-zinc-800 px-4 py-6 text-sm text-zinc-400">
                No detailed findings were returned by the backend for this scan yet.
              </p>
            ) : (
              <div className="rounded-md border border-zinc-800 bg-zinc-950/70">
                {findings.map((finding, index) => (
                  <div key={`${finding.title}-${index}`} className="border-b border-zinc-800 px-4 py-4 last:border-none">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-zinc-100">{finding.title}</p>
                        <p className="mt-2 text-sm leading-7 text-zinc-400">{finding.description}</p>
                      </div>
                      <SeverityBadge severity={finding.severity} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="rounded-md border border-zinc-800 bg-zinc-950/70 p-5">
            <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Scan status</p>
            <p className="mt-3 text-sm text-zinc-400">
              {job?.status === "running" || job?.status === "pending"
                ? "The scan is still processing. Results will refresh automatically until completion."
                : "The scan has finished and the summary above reflects the latest data."}
            </p>
          </section>
          {screenshot ? (
            <section className="rounded-md border border-zinc-800 bg-zinc-950/70 p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Screenshot</p>
              <img src={screenshot} alt="Scan screenshot" className="mt-4 w-full rounded-md border border-zinc-800" />
            </section>
          ) : null}
        </aside>
      </main>
    </div>
  );
}
