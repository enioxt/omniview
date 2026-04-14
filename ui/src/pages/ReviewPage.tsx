/**
 * ReviewPage — video list + event gallery + inline review.
 *
 * Layout:
 *   Left panel: video list
 *   Right panel: EventGallery with FiltersBar
 *   Click event → EventDetailPage
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { listVideos, listEvents } from "../lib/api";
import { EventGallery } from "../components/EventGallery";
import { FiltersBar, type EventFilters } from "../components/FiltersBar";
import type { Video, MotionEvent } from "../types";

const DEFAULT_FILTERS: EventFilters = { status: "all", falseAlarm: null, minScore: 0 };

export default function ReviewPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [events, setEvents] = useState<MotionEvent[]>([]);
  const [filters, setFilters] = useState<EventFilters>(DEFAULT_FILTERS);
  const [loadingVideos, setLoadingVideos] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // Load videos
  useEffect(() => {
    listVideos({ status: "completed" })
      .then((vids) => {
        setVideos(vids);
        if (vids.length > 0) setSelectedVideo(vids[0]);
      })
      .catch(console.error)
      .finally(() => setLoadingVideos(false));
  }, []);

  // Load events when video changes
  useEffect(() => {
    if (!selectedVideo) return;
    setLoadingEvents(true);
    listEvents(selectedVideo.id, {
      status: filters.status !== "all" ? filters.status : undefined,
      min_score: filters.minScore > 0 ? filters.minScore : undefined,
    })
      .then(setEvents)
      .catch(console.error)
      .finally(() => setLoadingEvents(false));
  }, [selectedVideo, filters]);

  const filteredEvents = events.filter((ev) => {
    if (filters.falseAlarm === true) {
      // false_alarm events have is_false_alarm in their review — approximate via dismissed
      return ev.event_status === "dismissed";
    }
    return true;
  });

  if (loadingVideos) {
    return <div className="p-6 text-sm text-gray-500">{t("review.loading")}</div>;
  }

  return (
    <div className="flex h-full">
      {/* Video list */}
      <aside className="w-56 border-r border-gray-800 overflow-y-auto shrink-0">
        <div className="px-3 py-3 border-b border-gray-800">
          <p className="text-xs font-medium text-gray-400">{t("review.videos")}</p>
        </div>
        {videos.length === 0 ? (
          <p className="px-3 py-4 text-xs text-gray-600">{t("review.no_videos")}</p>
        ) : (
          <ul>
            {videos.map((v) => (
              <li key={v.id}>
                <button
                  onClick={() => setSelectedVideo(v)}
                  className={[
                    "w-full text-left px-3 py-2.5 border-b border-gray-800/50 transition-colors",
                    selectedVideo?.id === v.id
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:bg-gray-800/50 hover:text-gray-200",
                  ].join(" ")}
                >
                  <p className="text-xs truncate">{v.source_name ?? v.id.slice(0, 8)}</p>
                  <p className="text-xs text-gray-600">{v.event_count} eventos</p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedVideo && (
          <>
            <FiltersBar filters={filters} onChange={setFilters} />
            {loadingEvents ? (
              <p className="text-xs text-gray-500 py-4">{t("review.loading_events")}</p>
            ) : (
              <EventGallery
                videoId={selectedVideo.id}
                events={filteredEvents}
                onSelectEvent={(ev: MotionEvent) =>
                  navigate(`/review/${selectedVideo.id}/events/${ev.id}`)
                }
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
