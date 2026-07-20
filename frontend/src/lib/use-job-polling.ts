"use client";

import { useEffect, useRef, useState } from "react";
import type { JobStatusResponse } from "./types";

const POLL_INTERVAL_MS = 2000;

export function useJobPolling(
  jobId: string | null,
  fetchJob: (jobId: string) => Promise<JobStatusResponse>
) {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    let cancelled = false;

    async function poll() {
      try {
        const data = await fetchJob(jobId!);
        if (cancelled) return;
        setStatus(data);
        setPollError(null);
        if (data.state === "completed" || data.state === "failed" || data.state === "stopped") {
          return;
        }
      } catch (err) {
        if (cancelled) return;
        // A single failed poll (dropped connection, backend mid-restart) must
        // not permanently kill polling -- surface the error but keep retrying,
        // since the backend may well recover on its own.
        setPollError(err instanceof Error ? err.message : "Failed to fetch job status");
      }
      timeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS);
    }

    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { status, pollError };
}
