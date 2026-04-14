import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/** Guards routes that require a logged-in user. */
export function RequireAuth() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <span className="text-sm text-gray-500">Verificando sessão…</span>
      </div>
    );
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
