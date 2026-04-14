/**
 * ExportPage — forensic ZIP export for completed videos.
 *
 * Flow:
 *   1. Load list of completed videos
 *   2. User selects a video
 *   3. POST /api/videos/{id}/export → browser download
 *   4. User can run `omniview-cli verify <zip>` to confirm HMAC
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listVideos } from "../lib/api";
import type { Video } from "../types";

export default function ExportPage() {
  const { t } = useTranslation();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listVideos({ status: "completed" })
      .then(setVideos)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleExport(video: Video) {
    setExporting(video.id);
    setError(null);
    try {
      // Trigger download via hidden anchor — avoids storing blob in memory
      const a = document.createElement("a");
      a.href = `/api/videos/${video.id}/export`;
      a.download = `omniview_export_${video.id.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao exportar");
    } finally {
      setTimeout(() => setExporting(null), 2000);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-lg font-semibold text-gray-100 mb-1">{t("export.title")}</h1>
      <p className="text-xs text-gray-500 mb-6">
        Exporta um ZIP forense com original, thumbnails, clips, provenance.json e relatório HTML.
        O manifesto inclui HMAC para verificação de integridade.
      </p>

      {/* CLI verify hint */}
      <div className="mb-6 p-3 bg-gray-900 rounded border border-gray-800 text-xs text-gray-500 font-mono">
        omniview-cli verify omniview_export_*.zip
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">{t("common.loading")}</p>
      ) : videos.length === 0 ? (
        <p className="text-sm text-gray-500">
          Nenhum vídeo processado disponível para exportação.
        </p>
      ) : (
        <div className="space-y-2">
          {videos.map((v) => (
            <div
              key={v.id}
              className="flex items-center justify-between p-4 bg-gray-900 rounded border border-gray-800"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-200 truncate">
                  {v.source_name ?? v.id.slice(0, 16)}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {v.event_count} eventos
                  {v.duration_ms
                    ? ` · ${Math.round(v.duration_ms / 1000)}s`
                    : ""}
                  {v.sha256
                    ? ` · sha256:${v.sha256.slice(0, 12)}…`
                    : ""}
                </p>
              </div>

              <button
                onClick={() => void handleExport(v)}
                disabled={exporting === v.id}
                className="ml-4 shrink-0 px-4 py-2 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-sm text-white transition-colors"
              >
                {exporting === v.id ? "Exportando…" : t("export.download")}
              </button>
            </div>
          ))}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      {/* Phase 4 note */}
      <div className="mt-8 p-3 bg-gray-900/50 rounded border border-gray-800/50 text-xs text-gray-600">
        <p className="font-medium mb-1">Phase 4 — Guard Brasil PII scan</p>
        <p>Exports futuros passarão pelo Guard Brasil para detectar PII em relatórios antes do download.</p>
      </div>
    </div>
  );
}
