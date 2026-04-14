import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LoginForm } from "../components/auth/LoginForm";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin(username: string, password: string) {
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate("/review", { replace: true });
    } catch {
      setError("Usuário ou senha inválidos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center">
      <div className="mb-8 text-center">
        <h1 className="text-xl font-semibold text-gray-100">OmniView</h1>
        <p className="text-xs text-gray-500 mt-1">Análise forense de vídeo</p>
      </div>
      <LoginForm onSubmit={handleLogin} error={error} loading={loading} />
    </div>
  );
}
