"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, Input, Navbar } from "@/components/entropy-ui";
import { quickScan, getAuthToken } from "@/lib/api";
import { useRouter } from "next/navigation";

import { quickScan, setActiveOrgId } from "@/lib/api";
const features = [
  {
    title: "Attack Surface Discovery",
    description: "Map exposed assets, TLS posture, and external dependencies before attackers do.",
  },
  {
    title: "Continuous Monitoring",
    description: "Track recurring issues and keep your team aligned on what needs attention first.",
  },
  {
    title: "AI Risk Prioritization",
    description: "Turn raw findings into a concise executive summary grounded in severity and context.",
  },
  {
    title: "Fast Demo Workflow",
    description: "Kick off a scan from one input and move straight into the live results experience.",
  },
];

export default function Home() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      if (!token) {
        // Require sign-in for starting scans; redirect to login
        router.push(`/login?next=/scan`);
        return;
      }

      const response = await quickScan(domain.trim());
      setActiveOrgId(response.org_id);
      window.location.assign(`/scan/${response.scan_job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start scanning");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Navbar />
      <main className="mx-auto flex max-w-7xl flex-col px-6 py-16 lg:px-8 lg:py-24">
        <section className="mx-auto flex max-w-4xl flex-col items-center text-center">
          <p className="text-sm uppercase tracking-[0.4em] text-zinc-500">Entropy security intelligence</p>
          <h1 className="mt-6 text-5xl font-semibold leading-[1.05] text-zinc-50 sm:text-6xl lg:text-7xl">
            Ship fast. <br /> Stay secure.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400 sm:text-xl">
            Run a full security scan from a single domain input and get executive-ready findings in minutes.
          </p>

          <form onSubmit={handleSubmit} className="mt-10 flex w-full max-w-2xl flex-col gap-3 sm:flex-row">
            <Input
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="Enter your domain"
              className="sm:flex-1"
            />
            <Button type="submit" disabled={loading} className="min-w-[140px]">
              {loading ? "Scanning..." : "Start Scan"}
            </Button>
          </form>
          {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
        </section>

        <section className="mt-20 grid gap-6 border-t border-zinc-800 pt-12 md:grid-cols-2 xl:grid-cols-4">
          {features.map((feature) => (
            <div key={feature.title} className="space-y-3">
              <p className="text-sm font-semibold text-zinc-100">{feature.title}</p>
              <p className="text-sm leading-7 text-zinc-400">{feature.description}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
