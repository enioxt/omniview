import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";

const links = [
  { to: "/ingest", labelKey: "nav.ingest" },
  { to: "/review", labelKey: "nav.review" },
  { to: "/export", labelKey: "nav.export" },
] as const;

export function Sidebar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();

  return (
    <aside className="w-52 flex flex-col bg-gray-900 border-r border-gray-800 shrink-0">
      <div className="px-4 py-5 border-b border-gray-800">
        <span className="text-sm font-semibold tracking-wider text-gray-100">OmniView</span>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.map(({ to, labelKey }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "block px-3 py-2 rounded text-sm transition-colors",
                isActive
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100",
              ].join(" ")
            }
          >
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="px-4 py-3 border-t border-gray-800 space-y-1">
          <p className="text-xs text-gray-500 truncate">{user.username}</p>
          <p className="text-xs text-gray-600">{user.role}</p>
          <button
            onClick={() => void logout()}
            className="mt-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {t("nav.logout")}
          </button>
        </div>
      )}
    </aside>
  );
}
