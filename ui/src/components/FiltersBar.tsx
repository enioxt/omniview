/**
 * FiltersBar — filter events by status, false_alarm, and min score.
 */
import { useTranslation } from "react-i18next";
import type { EventStatus } from "../types";

export interface EventFilters {
  status: EventStatus | "all";
  falseAlarm: boolean | null;
  minScore: number;
}

interface Props {
  filters: EventFilters;
  onChange: (f: EventFilters) => void;
}

const STATUS_OPTIONS: Array<{ value: EventFilters["status"]; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "pending_review", label: "Pendentes" },
  { value: "reviewed", label: "Revisados" },
  { value: "dismissed", label: "Descartados" },
];

export function FiltersBar({ filters, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-3 py-2">
      {/* Status */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-gray-500">{t("review.filter_status")}:</span>
        <div className="flex gap-1">
          {STATUS_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => onChange({ ...filters, status: value })}
              className={[
                "px-2 py-1 rounded text-xs border transition-colors",
                filters.status === value
                  ? "bg-gray-700 border-gray-500 text-white"
                  : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* False alarm toggle */}
      <label className="flex items-center gap-1.5 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={filters.falseAlarm === true}
          onChange={(e) =>
            onChange({ ...filters, falseAlarm: e.target.checked ? true : null })
          }
          className="accent-blue-500"
        />
        <span className="text-xs text-gray-400">{t("review.filter_false_alarm")}</span>
      </label>

      {/* Min score */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">{t("review.filter_min_score")}:</span>
        <input
          type="range"
          min={0}
          max={100}
          value={filters.minScore}
          onChange={(e) => onChange({ ...filters, minScore: Number(e.target.value) })}
          className="w-20 accent-blue-500"
        />
        <span className="text-xs text-gray-400 w-6">{filters.minScore}</span>
      </div>
    </div>
  );
}
