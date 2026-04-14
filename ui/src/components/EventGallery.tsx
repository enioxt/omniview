/**
 * EventGallery — lazy-loaded thumbnail grid for motion events.
 *
 * Each card shows:
 *   - thumbnail (WebP from API)
 *   - event index + timestamp
 *   - motion score badge
 *   - review status badge
 */
import { useTranslation } from "react-i18next";
import type { MotionEvent } from "../types";
import { getThumbnailUrl } from "../lib/api";

interface Props {
  videoId: string;
  events: MotionEvent[];
  selectedEventId?: string | null;
  onSelectEvent: (event: MotionEvent) => void;
}

function statusBadge(status: MotionEvent["event_status"]): string {
  switch (status) {
    case "reviewed": return "bg-green-700 text-green-200";
    case "dismissed": return "bg-gray-700 text-gray-400";
    default: return "bg-yellow-700 text-yellow-200";
  }
}

function formatMs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}:${String(m % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

export function EventGallery({ videoId, events, selectedEventId, onSelectEvent }: Props) {
  const { t } = useTranslation();

  if (events.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-6 text-center">{t("review.no_events")}</p>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {events.map((ev) => {
        const isSelected = ev.id === selectedEventId;
        const thumbUrl = getThumbnailUrl(videoId, ev.id);

        return (
          <button
            key={ev.id}
            onClick={() => onSelectEvent(ev)}
            className={[
              "group relative flex flex-col rounded overflow-hidden text-left transition-all",
              "bg-gray-900 border",
              isSelected
                ? "border-blue-500 ring-2 ring-blue-500"
                : "border-gray-700 hover:border-gray-500",
            ].join(" ")}
          >
            {/* Thumbnail */}
            <div className="aspect-video bg-gray-800 overflow-hidden">
              {ev.has_thumbnail ? (
                <img
                  src={thumbUrl}
                  alt={`Event ${ev.event_index + 1}`}
                  loading="lazy"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-600 text-xs">
                  {t("review.no_thumbnail")}
                </div>
              )}
            </div>

            {/* Info */}
            <div className="px-2 py-1.5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-300">#{ev.event_index + 1}</span>
                <span className="text-xs text-gray-500">{formatMs(ev.start_pts_ms)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className={`text-xs px-1.5 py-0.5 rounded ${statusBadge(ev.event_status)}`}>
                  {t(`review.status.${ev.event_status}`)}
                </span>
                <span className="text-xs text-gray-500">
                  {ev.peak_motion_score.toFixed(0)}
                </span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
