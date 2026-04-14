/**
 * ReviewPanel — label a motion event.
 *
 * Hotkeys (focus on panel):
 *   1 = person      2 = vehicle_car   3 = vehicle_moto
 *   4 = animal      5 = shadow        6 = bird
 *   9 = false_alarm  0 = other
 *   Enter = submit  Escape = cancel
 *
 * Reutilizável em: Gem Hunter, future labeling tools (ecosystem pattern).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { MotionEvent, ReviewLabel, Priority, ReviewRequest } from "../types";

interface Props {
  event: MotionEvent;
  onSubmit: (req: ReviewRequest) => Promise<void>;
  loading?: boolean;
}

const LABEL_HOTKEYS: Record<string, ReviewLabel> = {
  "1": "person",
  "2": "vehicle_car",
  "3": "vehicle_moto",
  "4": "animal",
  "5": "shadow",
  "6": "bird",
  "9": "false_alarm",
  "0": "other",
};

const LABELS: Array<{ key: string; value: ReviewLabel; label: string }> = [
  { key: "1", value: "person", label: "Pessoa" },
  { key: "2", value: "vehicle_car", label: "Carro" },
  { key: "3", value: "vehicle_moto", label: "Moto" },
  { key: "4", value: "animal", label: "Animal" },
  { key: "5", value: "shadow", label: "Sombra" },
  { key: "6", value: "bird", label: "Pássaro" },
  { key: "9", value: "false_alarm", label: "Falso alarme" },
  { key: "0", value: "other", label: "Outro" },
];

const PRIORITIES: Array<{ value: Priority; label: string }> = [
  { value: "low", label: "Baixa" },
  { value: "medium", label: "Média" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Crítica" },
];

export function ReviewPanel({ event, onSubmit, loading }: Props) {
  const { t } = useTranslation();
  const [label, setLabel] = useState<ReviewLabel | null>(null);
  const [priority, setPriority] = useState<Priority>("medium");
  const [notes, setNotes] = useState("");
  const [isFalseAlarm, setIsFalseAlarm] = useState(false);

  // Reset when event changes
  useEffect(() => {
    setLabel(null);
    setPriority("medium");
    setNotes("");
    setIsFalseAlarm(false);
  }, [event.id]);

  // Keyboard shortcuts
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const mapped = LABEL_HOTKEYS[e.key];
      if (mapped) {
        setLabel(mapped);
        if (mapped === "false_alarm") setIsFalseAlarm(true);
        return;
      }
      if (e.key === "Enter") {
        void handleSubmit();
      }
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label, priority, notes, isFalseAlarm]);

  async function handleSubmit() {
    await onSubmit({
      label_manual: label ?? undefined,
      is_false_alarm: isFalseAlarm,
      priority,
      notes: notes.trim() || undefined,
    });
  }

  return (
    <div className="flex flex-col gap-4 p-4 bg-gray-900 rounded border border-gray-800">
      <div>
        <p className="text-xs text-gray-500 mb-2">{t("review.label")} <span className="text-gray-600">(hotkeys 1–9)</span></p>
        <div className="flex flex-wrap gap-2">
          {LABELS.map(({ key, value, label: display }) => (
            <button
              key={value}
              onClick={() => {
                setLabel(value);
                if (value === "false_alarm") setIsFalseAlarm(true);
                else setIsFalseAlarm(false);
              }}
              className={[
                "px-2 py-1 rounded text-xs border transition-colors",
                label === value
                  ? "bg-blue-700 border-blue-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500",
              ].join(" ")}
            >
              <kbd className="text-gray-500 mr-1">{key}</kbd>{display}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs text-gray-500 mb-2">{t("review.priority")}</p>
        <div className="flex gap-2">
          {PRIORITIES.map(({ value, label: display }) => (
            <button
              key={value}
              onClick={() => setPriority(value)}
              className={[
                "px-2 py-1 rounded text-xs border transition-colors",
                priority === value
                  ? "bg-gray-700 border-gray-400 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500",
              ].join(" ")}
            >
              {display}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-500 block mb-1">{t("review.notes")}</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 resize-none focus:outline-none focus:border-gray-500"
          placeholder={t("review.notes_placeholder")}
        />
      </div>

      <button
        onClick={() => void handleSubmit()}
        disabled={loading}
        className="w-full py-2 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-sm font-medium text-white transition-colors"
      >
        {loading ? t("review.saving") : `${t("review.save")} (Enter)`}
      </button>
    </div>
  );
}
