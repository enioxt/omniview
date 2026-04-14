/**
 * EventTimeline — horizontal timeline bar with clickable event markers.
 *
 * Shows all motion events for a video as colored markers proportional
 * to the video's duration. Clicking a marker seeks the video and
 * highlights the selected event.
 */
import type { MotionEvent } from "../types";

interface Props {
  events: MotionEvent[];
  durationMs: number;
  selectedEventId?: string | null;
  currentMs?: number;
  onSelectEvent: (event: MotionEvent) => void;
}

function statusColor(status: MotionEvent["event_status"]): string {
  switch (status) {
    case "reviewed": return "bg-green-500";
    case "dismissed": return "bg-gray-600";
    default: return "bg-yellow-500";
  }
}

export function EventTimeline({
  events,
  durationMs,
  selectedEventId,
  currentMs = 0,
  onSelectEvent,
}: Props) {
  if (durationMs <= 0) return null;

  const playheadPct = Math.min((currentMs / durationMs) * 100, 100);

  return (
    <div className="relative w-full h-8 bg-gray-800 rounded overflow-hidden select-none">
      {/* Playhead */}
      <div
        className="absolute top-0 w-0.5 h-full bg-white/60 pointer-events-none z-10"
        style={{ left: `${playheadPct}%` }}
      />

      {/* Event markers */}
      {events.map((ev) => {
        const leftPct = (ev.start_pts_ms / durationMs) * 100;
        const widthPct = Math.max(((ev.end_pts_ms - ev.start_pts_ms) / durationMs) * 100, 0.3);
        const isSelected = ev.id === selectedEventId;

        return (
          <button
            key={ev.id}
            className={[
              "absolute top-1 h-6 rounded-sm transition-all cursor-pointer",
              statusColor(ev.event_status),
              isSelected ? "opacity-100 ring-2 ring-white z-20" : "opacity-70 hover:opacity-100 z-10",
            ].join(" ")}
            style={{ left: `${leftPct}%`, width: `${widthPct}%`, minWidth: "4px" }}
            title={`Evento #${ev.event_index + 1} — score ${ev.peak_motion_score.toFixed(1)}`}
            onClick={() => onSelectEvent(ev)}
          />
        );
      })}
    </div>
  );
}
