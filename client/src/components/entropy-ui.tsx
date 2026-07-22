import Link from "next/link";
import type { ReactNode } from "react";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function Button({
  children,
  className = "",
  variant = "default",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "ghost" }) {
  const styles =
    variant === "ghost"
      ? "border border-zinc-800 bg-transparent text-zinc-100 hover:bg-zinc-900"
      : "bg-white text-black hover:bg-zinc-200";

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors",
        styles,
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({
  className = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-zinc-800 bg-black px-4 py-3 text-sm text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-zinc-600",
        className,
      )}
      {...props}
    />
  );
}

export function Navbar() {
  return (
    <nav className="border-b border-zinc-800">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
        <Link href="/" className="text-sm font-semibold uppercase tracking-[0.3em] text-zinc-100">
          Entropy
        </Link>
        <div className="hidden items-center gap-8 text-sm text-zinc-400 md:flex">
          <Link href="/dashboard" className="transition hover:text-zinc-100">
            Dashboard
          </Link>
          <Link href="/dashboard" className="transition hover:text-zinc-100">
            Scans
          </Link>
          <Link href="/login" className="transition hover:text-zinc-100">
            Settings
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-zinc-400 transition hover:text-zinc-100">
            Sign in
          </Link>
          <Link href="/register" className="rounded-md border border-zinc-800 px-3 py-2 text-sm text-zinc-100">
            Join
          </Link>
        </div>
      </div>
    </nav>
  );
}

export function SeverityBadge({ severity }: { severity?: string | null }) {
  const normalized = (severity ?? "info").toLowerCase();
  const tone =
    normalized === "critical"
      ? "text-rose-300"
      : normalized === "high"
        ? "text-orange-300"
        : normalized === "medium"
          ? "text-amber-300"
          : normalized === "low"
            ? "text-sky-300"
            : "text-zinc-300";

  return (
    <span className={cn("flex items-center gap-2 text-sm font-medium", tone)}>
      <span className="h-2.5 w-2.5 rounded-full bg-current" />
      {normalized}
    </span>
  );
}

export function ScanRow({
  title,
  status,
  timestamp,
  onClick,
}: {
  title: string;
  status: string;
  timestamp: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between border-b border-zinc-800 px-0 py-4 text-left transition hover:bg-zinc-950"
    >
      <div>
        <p className="font-medium text-zinc-100">{title}</p>
        <p className="mt-1 text-sm text-zinc-500">{timestamp}</p>
      </div>
      <div className="flex items-center gap-3 text-sm text-zinc-400">
        <span className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-current" />
          {status}
        </span>
      </div>
    </button>
  );
}

export function Section({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-5">
      <div className="space-y-2">
        {eyebrow ? <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">{eyebrow}</p> : null}
        <h2 className="text-2xl font-semibold text-zinc-100">{title}</h2>
      </div>
      {children}
    </section>
  );
}
