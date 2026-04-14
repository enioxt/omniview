/**
 * IngestPage — drag-and-drop video upload with real-time scan progress.
 *
 * Flow:
 *   1. User drops/selects file
 *   2. POST /api/videos (multipart) with upload progress bar
 *   3. Engine starts async scan → WebSocket reports progress
 *   4. On done: redirect to EventDetail or Review page
 */
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { uploadVideo } from "../lib/api";
import { useVideoScanProgress } from "../hooks/useWebSocket";
import type { Video } from "../types";

export default function IngestPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [uploadedVideo, setUploadedVideo] = useState<Video | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const scanProgress = useVideoScanProgress(uploadedVideo?.id ?? null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setUploadPct(0);
      try {
        const video = await uploadVideo(file, setUploadPct);
        setUploadedVideo(video);
        setUploadPct(100);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao enviar arquivo");
        setUploadPct(null);
      }
    },
    []
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) void handleFile(file);
    },
    [handleFile]
  );

  // Navigate when scan completes
  if (scanProgress.done && uploadedVideo) {
    setTimeout(() => navigate(`/review`), 1200);
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold text-gray-100 mb-6">{t("ingest.title")}</h1>

      {/* Dropzone */}
      {uploadPct === null && (
        <label
          className={[
            "flex flex-col items-center justify-center w-full h-48 rounded-lg border-2 border-dashed cursor-pointer transition-colors",
            dragging
              ? "border-blue-500 bg-blue-950/30"
              : "border-gray-700 bg-gray-900 hover:border-gray-500",
          ].join(" ")}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <span className="text-3xl mb-2">🎥</span>
          <span className="text-sm text-gray-300">{t("ingest.drop_hint")}</span>
          <span className="text-xs text-gray-500 mt-1">{t("ingest.formats_hint")}</span>
          <input
            type="file"
            accept=".mp4,.avi,.mkv,.mov,.mts,.m2ts,.ts"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
        </label>
      )}

      {/* Upload progress */}
      {uploadPct !== null && !uploadedVideo && (
        <ProgressBar label={t("ingest.uploading")} pct={uploadPct} />
      )}

      {/* Scan progress */}
      {uploadedVideo && !scanProgress.done && !scanProgress.error && (
        <ProgressBar
          label={`${t("ingest.scanning")}: ${scanProgress.stage}`}
          pct={scanProgress.pct}
        />
      )}

      {/* Done */}
      {scanProgress.done && (
        <div className="flex flex-col items-center py-8 gap-2">
          <span className="text-green-400 text-2xl">✓</span>
          <p className="text-sm text-gray-300">
            {t("ingest.done")} — {scanProgress.eventCount} {t("ingest.events_found")}
          </p>
          <p className="text-xs text-gray-500">{t("ingest.redirecting")}</p>
        </div>
      )}

      {/* Error */}
      {(error ?? scanProgress.error) && (
        <p className="text-sm text-red-400 mt-4">{error ?? scanProgress.error}</p>
      )}
    </div>
  );
}

function ProgressBar({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
