"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getIngestionProgress } from "@/lib/api";
import type { IngestionProgress } from "@/lib/types";

export function useIngestionProgress(docId: string | null, active: boolean) {
  const [progress, setProgress] = useState<IngestionProgress | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!docId || !active) {
      stop();
      return;
    }

    const poll = async () => {
      try {
        const p = await getIngestionProgress(docId);
        setProgress(p);
        if (p.status === "completed" || p.status === "failed") {
          stop();
        }
      } catch {
        stop();
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 1500);

    return stop;
  }, [docId, active, stop]);

  return { progress, stop };
}
