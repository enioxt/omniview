/**
 * useAuth — portable auth state hook.
 *
 * Separated from AuthContext.tsx so this logic can be copy-pasted into
 * @egos/ui-auth when that package is created (ecosystem alignment).
 * No React imports here — pure state + API calls.
 */
import { useContext } from "react";
import { AuthContext, type AuthContextValue } from "../contexts/AuthContext";

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
