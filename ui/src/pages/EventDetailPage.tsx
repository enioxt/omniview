/**
 * EventDetailPage — VideoPlayer + EventTimeline + ReviewPanel side-by-side.
 *
 * Layout:
 *   Left: VideoPlayer (clip) + EventTimeline (full video events)
 *   Right: ReviewPanel + event metadata
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { getEvent, getVideo, listEvents, submitReview, getClipUrl } from "../lib/api";
import { VideoPlayer } from "../components/VideoPlayer";
import { EventTimeline } from "../components/EventTimeline";
import { ReviewPanel } from "../components/ReviewPanel";
import type { Video, MotionEvent, ReviewRequest } from "../types";

export default function EventDetailPage() {
  const { videoId, eventId } = useParams<{ videoId: string; eventId: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [video, setVideo] = useState<Video | null>(null);
  const [event, setEvent] = useState<MotionEvent | null>(null);
  const [allEvents, setAllEvents] = useState<MotionEvent[]>([]);
  const [currentMs, setCurrentMs] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!videoId || !eventId) return;
    Promise.all([
      getVideo(videoId),
      getEvent(videoId, eventId),
      listEvents(videoId),
    ]).then(([v, ev, evs]) => {
      setVideo(v);
      setEvent(ev);
      setAllEvents(evs);
      setCurrentMs(ev.start_pts_ms);
    }).catch(console.error);
  }, [videoId, eventId]);

  async function handleReview(req: ReviewRequest) {
    if (!videoId || !eventId) return;
    setSaving(true);
    try {
      await submitReview(videoId, eventId, req);
      setSaved(true);
      // Auto-advance to next event after 800ms
      setTimeout(() => {
        const idx = allEvents.findIndex((e) => e.id === eventId);
        const next = allEvents[idx + 1];
        if (next) {
          navigate(`/review/${videoId}/events/${next.id}`, { replace: true });
        } else {
          navigate(`/review`, { replace: true });
        }
      }, 800);
    } finally {
      setSaving(false);
    }
  }

  if (!video || !event) {
    return <div className="p-6 text-sm text-gray-500">{t("review.loading")}</div>;
  }

  const clipUrl = getClipUrl(video.id, event.id);

  return (
    <div className="p-4 flex flex-col gap-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-xs text-gray-500 hover:text-gray-300"
        >
          ← {t("review.back")}
        </button>
        <span className="text-sm text-gray-400">
          {video.source_name ?? video.id.slice(0, 8)} — Evento #{event.event_index + 1}
        </span>
        {saved && <span className="text-xs text-green-400 ml-auto">✓ {t("review.saved")}</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
        {/* Left: Video + Timeline */}
        <div className="flex flex-col gap-3">
          <VideoPlayer
            src={clipUrl}
            seekToMs={event.start_pts_ms}
            onTimeUpdate={setCurrentMs}
          />
          <EventTimeline
            events={allEvents}
            durationMs={video.duration_ms ?? 0}
            selectedEventId={event.id}
            currentMs={currentMs}
            onSelectEvent={(ev) =>
              navigate(`/review/${video.id}/events/${ev.id}`, { replace: true })
            }
          />

          {/* Event metadata */}
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 bg-gray-900 rounded p-3">
            <span>Score pico: <b className="text-gray-300">{event.peak_motion_score.toFixed(1)}</b></span>
            <span>Área total: <b className="text-gray-300">{event.total_motion_area.toFixed(0)}</b></span>
            <span>Início: <b className="text-gray-300">{msToHms(event.start_pts_ms)}</b></span>
            <span>Fim: <b className="text-gray-300">{msToHms(event.end_pts_ms)}</b></span>
          </div>
        </div>

        {/* Right: ReviewPanel */}
        <ReviewPanel event={event} onSubmit={handleReview} loading={saving} />
      </div>
    </div>
  );
}

function msToHms(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  return `${String(h).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
