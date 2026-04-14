/**
 * ExportPage — placeholder for Phase 3.
 *
 * Phase 3 will implement:
 *   - ZIP with original + thumbnails + clips + provenance + reviews
 *   - HTML report (Jinja2) in ZIP
 *   - Manifest with SHA-256 per file + HMAC signature
 */
import { useTranslation } from "react-i18next";

export default function ExportPage() {
  const { t } = useTranslation();

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold text-gray-100 mb-2">{t("export.title")}</h1>
      <p className="text-sm text-gray-500">{t("export.coming_soon")}</p>
      <div className="mt-6 p-4 bg-gray-900 rounded border border-gray-800 text-xs text-gray-600 space-y-1">
        <p>Phase 3 — Export forense:</p>
        <ul className="list-disc ml-4 space-y-0.5">
          <li>ZIP com original + thumbnails + clips + provenance</li>
          <li>Relatório HTML com chain-of-custody</li>
          <li>Manifesto SHA-256 por arquivo + assinatura HMAC</li>
          <li>omniview-cli verify &lt;zip&gt;</li>
        </ul>
      </div>
    </div>
  );
}
