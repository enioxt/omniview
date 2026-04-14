import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const IngestPage = lazy(() => import("./pages/IngestPage"));
const ReviewPage = lazy(() => import("./pages/ReviewPage"));
const EventDetailPage = lazy(() => import("./pages/EventDetailPage"));
const ExportPage = lazy(() => import("./pages/ExportPage"));

function Loading() {
  return (
    <div className="flex h-screen items-center justify-center bg-gray-950">
      <span className="text-sm text-gray-500">Carregando…</span>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route element={<Layout />}>
                <Route index element={<Navigate to="/review" replace />} />
                <Route path="/ingest" element={<IngestPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/review/:videoId/events/:eventId" element={<EventDetailPage />} />
                <Route path="/export" element={<ExportPage />} />
              </Route>
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
