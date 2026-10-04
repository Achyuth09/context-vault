const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export type Stats = {
  chunks: number;
  by_doc: Record<string, number>;
  by_status: Record<string, number>;
  conflicts_total: number;
  conflicts_real: number;
};

export type ChunkRow = {
  id: string;
  text: string;
  doc_id: string;
  status: string;
  updated_at: string;
  ingested_at: string;
  chunk_index: number;
  source_path: string;
};

export type ConflictRow = {
  id: string;
  fact_a: string;
  fact_b: string;
  contradict: boolean;
  reason: string;
  created_at: string;
  doc_id_a?: string;
  doc_id_b?: string;
  query?: string;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed (${res.status}). Is the API running on ${API_URL}?`);
  }
  return res.json() as Promise<T>;
}

export function apiBase(): string {
  return API_URL;
}

export async function fetchStats(): Promise<Stats> {
  return getJson<Stats>("/api/stats");
}

export async function fetchChunks(): Promise<ChunkRow[]> {
  const data = await getJson<{ chunks: ChunkRow[] }>("/api/chunks");
  return data.chunks;
}

export async function fetchConflicts(): Promise<ConflictRow[]> {
  const data = await getJson<{ conflicts: ConflictRow[] }>("/api/conflicts?only_real=true");
  return data.conflicts;
}

export async function markDocStale(docId: string): Promise<{ chunks_updated: number }> {
  const res = await fetch(`${API_URL}/api/docs/${encodeURIComponent(docId)}/stale`, {
    method: "POST",
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* keep status */
    }
    throw new Error(`Mark stale failed (${detail})`);
  }
  return res.json() as Promise<{ chunks_updated: number }>;
}
