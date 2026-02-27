"use client";

import { useState, useEffect, useCallback } from "react";
import { getCatalog, ingestDoc, removeDoc } from "@/lib/api";
import type { DocSource } from "@/lib/types";

export function useDocSources() {
  const [sources, setSources] = useState<DocSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = useCallback(async () => {
    try {
      const data = await getCatalog();
      setSources(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load catalog");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const triggerIngest = useCallback(
    async (docId: string) => {
      // Optimistically mark as in_progress
      setSources((prev) =>
        prev.map((s) => (s.id === docId ? { ...s, status: "in_progress" } : s))
      );
      try {
        await ingestDoc(docId);
        // Refresh to get final state
        await fetchSources();
      } catch (e) {
        setSources((prev) =>
          prev.map((s) =>
            s.id === docId
              ? { ...s, status: "failed", error_message: e instanceof Error ? e.message : "Unknown error" }
              : s
          )
        );
      }
    },
    [fetchSources]
  );

  const triggerRemove = useCallback(
    async (docId: string) => {
      try {
        await removeDoc(docId);
        await fetchSources();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to remove");
      }
    },
    [fetchSources]
  );

  return { sources, loading, error, refetch: fetchSources, triggerIngest, triggerRemove };
}
