/**
 * LoginForm — UI only, no business logic.
 * Business logic lives in hooks/useAuth.ts (portable to @egos/ui-auth).
 */
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  onSubmit: (username: string, password: string) => Promise<void>;
  error?: string | null;
  loading?: boolean;
}

export function LoginForm({ onSubmit, error, loading }: Props) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit(username, password);
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="w-full max-w-sm space-y-4">
      <div>
        <label className="block text-xs text-gray-400 mb-1">{t("auth.username")}</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-gray-500"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">{t("auth.password")}</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-gray-500"
        />
      </div>

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-sm font-medium text-white transition-colors"
      >
        {loading ? t("auth.logging_in") : t("auth.login")}
      </button>
    </form>
  );
}
