"use client";

import { useCallback, useEffect, useState } from "react";
import {
  apiBase,
  fetchChunks,
  fetchConflicts,
  fetchStats,
  markDocStale,
  type ChunkRow,
  type ConflictRow,
  type Stats,
} from "../lib/api";

function statusStyle(status: string): { color: string; bg: string } {
  switch (status) {
    case "contested":
      return { color: "var(--contested)", bg: "var(--contested-soft)" };
    case "stale":
      return { color: "var(--stale)", bg: "var(--stale-soft)" };
    case "aging":
      return { color: "var(--aging)", bg: "var(--aging-soft)" };
    default:
      return { color: "var(--fresh)", bg: "var(--fresh-soft)" };
  }
}

function StatusMark({ status }: { status: string }) {
  const s = statusStyle(status);
  return (
    <span
      className="inline-flex items-center gap-2 mono text-xs uppercase tracking-wide"
      style={{ color: s.color }}
    >
      <span className="status-dot" style={{ background: s.color }} />
      {status}
    </span>
  );
}

function preview(text: string, n = 110): string {
  const one = text.replace(/\s+/g, " ").trim();
  return one.length > n ? `${one.slice(0, n)}…` : one;
}

export default function HealthDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [chunks, setChunks] = useState<ChunkRow[]>([]);
  const [conflicts, setConflicts] = useState<ConflictRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingDoc, setPendingDoc] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, f] = await Promise.all([
        fetchStats(),
        fetchChunks(),
        fetchConflicts(),
      ]);
      setStats(s);
      setChunks(c);
      setConflicts(f);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load vault health");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const markStale = useCallback(
    async (docId: string) => {
      setPendingDoc(docId);
      setActionError(null);
      try {
        await markDocStale(docId);
        await load();
      } catch (e) {
        setActionError(e instanceof Error ? e.message : "Mark stale failed");
      } finally {
        setPendingDoc(null);
      }
    },
    [load],
  );

  const byStatus = stats?.by_status ?? {};
  const seenDocs = new Set<string>();
  const firstRowOfDoc = new Set<string>();
  const docCanMark = new Set<string>();
  for (const row of chunks) {
    if (!seenDocs.has(row.doc_id)) {
      seenDocs.add(row.doc_id);
      firstRowOfDoc.add(row.id);
    }
    if (row.status !== "stale") docCanMark.add(row.doc_id);
  }

  return (
    <div className="min-h-screen">
      <header className="relative overflow-hidden px-6 pb-14 pt-10 sm:px-10 sm:pt-14">
        <div className="rise mx-auto max-w-5xl">
          <p className="mono text-sm tracking-[0.18em] text-[var(--accent)]">
            CONTEXT VAULT
          </p>
          <h1 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Context health
          </h1>
          <p className="mt-4 max-w-xl text-base text-[var(--ink-muted)] sm:text-lg">
            Which knowledge is still trustworthy — fresh, aging, stale, or contested.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-md bg-[var(--ink)] px-4 py-2 text-sm font-medium text-[var(--bg)] transition hover:opacity-90"
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            <span className="mono text-xs text-[var(--ink-muted)]">
              API {apiBase()}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 pb-20 sm:px-10">
        {actionError && (
          <div
            className="rise mb-8 border border-[var(--stale)] bg-[var(--stale-soft)] px-4 py-3 text-sm"
            role="alert"
          >
            {actionError}
          </div>
        )}

        {error && (
          <div
            className="rise mb-8 border border-[var(--contested)] bg-[var(--contested-soft)] px-4 py-3 text-sm"
            role="alert"
          >
            {error}
            <div className="mt-1 text-[var(--ink-muted)]">
              Start the API:{" "}
              <span className="mono">
                uvicorn context_vault.api:app --reload --port 8000
              </span>
            </div>
          </div>
        )}

        <section className="rise rise-delay-1 panel mb-10 px-5 py-6 sm:px-7">
          <h2 className="text-lg font-semibold">Pulse</h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Stored chunk statuses from Chroma (explicit stamps win over age alone).
          </p>
          <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
            {(
              [
                ["fresh", byStatus.fresh ?? 0],
                ["aging", byStatus.aging ?? 0],
                ["stale", byStatus.stale ?? 0],
                ["contested", byStatus.contested ?? 0],
              ] as const
            ).map(([label, n]) => {
              const s = statusStyle(label);
              return (
                <div key={label}>
                  <div className="mono text-xs uppercase tracking-wide" style={{ color: s.color }}>
                    {label}
                  </div>
                  <div className="mt-2 text-3xl font-semibold tabular-nums">{n}</div>
                </div>
              );
            })}
          </div>
          <p className="mt-6 mono text-xs text-[var(--ink-muted)]">
            chunks={stats?.chunks ?? "—"} · real conflicts={stats?.conflicts_real ?? "—"} /{" "}
            {stats?.conflicts_total ?? "—"} logged
          </p>
        </section>

        <section className="rise rise-delay-2 mb-12">
          <h2 className="text-lg font-semibold">Documents</h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Every indexed chunk with provenance.
          </p>
          <div className="mt-5 overflow-x-auto border-t border-[var(--line)]">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="mono text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                  <th className="py-3 pr-4 font-medium">Status</th>
                  <th className="py-3 pr-4 font-medium">Doc</th>
                  <th className="py-3 pr-4 font-medium">Updated</th>
                  <th className="py-3 font-medium">Preview</th>
                </tr>
              </thead>
              <tbody>
                {chunks.map((row) => (
                  <tr key={row.id} className="border-t border-[var(--line)] align-top">
                    <td className="py-3 pr-4">
                      <StatusMark status={row.status} />
                      {firstRowOfDoc.has(row.id) && docCanMark.has(row.doc_id) && (
                        <button
                          type="button"
                          onClick={() => void markStale(row.doc_id)}
                          disabled={pendingDoc !== null}
                          className="mt-2 block rounded-md border border-[var(--line)] px-2 py-1 text-xs text-[var(--ink)] hover:bg-[var(--stale-soft)] disabled:opacity-50"
                        >
                          {pendingDoc === row.doc_id ? "Marking…" : "Mark stale"}
                        </button>
                      )}
                    </td>
                    <td className="py-3 pr-4 mono text-xs">{row.doc_id}</td>
                    <td className="py-3 pr-4 mono text-xs text-[var(--ink-muted)]">
                      {row.updated_at.slice(0, 10) || "—"}
                    </td>
                    <td className="py-3 text-[var(--ink-muted)]">{preview(row.text)}</td>
                  </tr>
                ))}
                {!loading && chunks.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-6 text-[var(--ink-muted)]">
                      No chunks yet. Run{" "}
                      <span className="mono">python -m context_vault.cli ingest</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rise rise-delay-3">
          <h2 className="text-lg font-semibold">Conflicts</h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Only real contradictions (Gemini said contradict=true).
          </p>
          <ul className="mt-5 space-y-0 border-t border-[var(--line)]">
            {conflicts.map((c) => (
              <li key={c.id} className="border-b border-[var(--line)] py-5">
                <div className="flex flex-wrap items-baseline gap-3">
                  <StatusMark status="contested" />
                  <span className="mono text-xs text-[var(--ink-muted)]">
                    {c.doc_id_a || "?"} vs {c.doc_id_b || "?"}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium">{c.reason}</p>
                <p className="mt-2 text-sm text-[var(--ink-muted)]">
                  A: {preview(c.fact_a, 140)}
                </p>
                <p className="mt-1 text-sm text-[var(--ink-muted)]">
                  B: {preview(c.fact_b, 140)}
                </p>
              </li>
            ))}
            {!loading && conflicts.length === 0 && (
              <li className="py-6 text-sm text-[var(--ink-muted)]">
                No real conflicts logged. Run{" "}
                <span className="mono">
                  python -m context_vault.cli conflicts &quot;What is our API version?&quot;
                </span>
              </li>
            )}
          </ul>
        </section>
      </main>
    </div>
  );
}
