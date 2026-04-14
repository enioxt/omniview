/**
 * OmniView API client — wraps all 19 FastAPI endpoints.
 * Cookie-based auth (httpOnly "omniview_session") is handled automatically by axios.
 */
import axios from "axios";
import type {
  Video,
  MotionEvent,
  Review,
  ReviewRequest,
  User,
} from "../types";

const http = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<User> {
  const { data } = await http.post<User>("/auth/login", { username, password });
  return data;
}

export async function logout(): Promise<void> {
  await http.post("/auth/logout");
}

export async function getMe(): Promise<User> {
  const { data } = await http.get<User>("/auth/me");
  return data;
}

// ── Videos ───────────────────────────────────────────────────────────────────

export interface VideoListParams {
  status?: string;
  offset?: number;
  limit?: number;
}

export async function listVideos(params?: VideoListParams): Promise<Video[]> {
  const { data } = await http.get<Video[]>("/videos", { params });
  return data;
}

export async function getVideo(id: string): Promise<Video> {
  const { data } = await http.get<Video>(`/videos/${id}`);
  return data;
}

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void
): Promise<Video> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await http.post<Video>("/videos", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function deleteVideo(id: string): Promise<void> {
  await http.delete(`/videos/${id}`);
}

export async function getProvenance(id: string): Promise<unknown> {
  const { data } = await http.get(`/videos/${id}/provenance`);
  return data;
}

// ── Events ────────────────────────────────────────────────────────────────────

export interface EventListParams {
  status?: string;
  min_score?: number;
  offset?: number;
  limit?: number;
}

export async function listEvents(
  videoId: string,
  params?: EventListParams
): Promise<MotionEvent[]> {
  const { data } = await http.get<MotionEvent[]>(`/videos/${videoId}/events`, { params });
  return data;
}

export async function getEvent(videoId: string, eventId: string): Promise<MotionEvent> {
  const { data } = await http.get<MotionEvent>(`/videos/${videoId}/events/${eventId}`);
  return data;
}

export function getThumbnailUrl(videoId: string, eventId: string): string {
  return `/api/videos/${videoId}/events/${eventId}/thumbnail`;
}

export function getClipUrl(videoId: string, eventId: string): string {
  return `/api/videos/${videoId}/events/${eventId}/clip`;
}

export async function submitReview(
  videoId: string,
  eventId: string,
  body: ReviewRequest
): Promise<Review> {
  const { data } = await http.post<Review>(
    `/videos/${videoId}/events/${eventId}/review`,
    body
  );
  return data;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<{ status: string; version: string }> {
  const { data } = await http.get("/health");
  return data;
}

// ── Interceptor: redirect to login on 401 ────────────────────────────────────

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      // Let AuthContext handle the redirect via its own listener
      window.dispatchEvent(new Event("omniview:unauthorized"));
    }
    return Promise.reject(err);
  }
);
