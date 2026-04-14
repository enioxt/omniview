/**
 * useWebSocket — scan progress WebSocket for a video.
 *
 * Connects to ws://host/ws/videos/{videoId}/progress
 * Messages: { type: "progress", pct: number, stage: string }
 *           { type: "done", event_count: number }
 *           { type: "error", message: string }
 */
import { useEffect, useRef, useState } from "react";

export interface ScanProgress {
  pct: number;
  stage: string;
  done: boolean;
  eventCount: number | null;
  error: string | null;
}

const INITIAL: ScanProgress = {
  pct: 0,
  stage: "waiting",
  done: false,
  eventCount: null,
  error: null,
};

export function useVideoScanProgress(videoId: string | null): ScanProgress {
  const [progress, setProgress] = useState<ScanProgress>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!videoId) return;
    setProgress(INITIAL);

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/videos/${videoId}/progress`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string) as Record<string, unknown>;
        if (msg.type === "progress") {
          setProgress((p) => ({ ...p, pct: Number(msg.pct), stage: String(msg.stage) }));
        } else if (msg.type === "done") {
          setProgress((p) => ({ ...p, done: true, pct: 100, eventCount: Number(msg.event_count) }));
          ws.close();
        } else if (msg.type === "error") {
          setProgress((p) => ({ ...p, error: String(msg.message) }));
          ws.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () =>
      setProgress((p) => ({ ...p, error: "WebSocket connection failed" }));

    return () => ws.close();
  }, [videoId]);

  return progress;
}
