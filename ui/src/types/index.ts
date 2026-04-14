export type VideoStatus =
  | "uploaded"
  | "hashing"
  | "quarantine"
  | "scanning"
  | "processing"
  | "completed"
  | "failed";

export type EventStatus = "pending_review" | "reviewed" | "dismissed";

export type ReviewLabel =
  | "person"
  | "vehicle_car"
  | "vehicle_moto"
  | "animal"
  | "shadow"
  | "bird"
  | "false_alarm"
  | "other";

export type Priority = "low" | "medium" | "high" | "critical";

export type UserRole = "admin" | "reviewer" | "viewer";

export interface Video {
  id: string;
  status: VideoStatus;
  sha256: string | null;
  source_name: string | null;
  duration_ms: number | null;
  fps_nominal: number | null;
  width: number | null;
  height: number | null;
  ingested_at: string;
  event_count: number;
}

export interface MotionEvent {
  id: string;
  video_id: string;
  event_index: number;
  start_pts_ms: number;
  end_pts_ms: number;
  peak_motion_score: number;
  total_motion_area: number;
  event_status: EventStatus;
  has_thumbnail: boolean;
  has_clip: boolean;
}

export interface Review {
  id: string;
  event_id: string;
  label_manual: ReviewLabel | null;
  is_false_alarm: boolean;
  priority: Priority;
  notes: string | null;
  reviewer_id: string | null;
  created_at: string;
}

export interface ReviewRequest {
  label_manual?: ReviewLabel;
  is_false_alarm: boolean;
  priority: Priority;
  notes?: string;
}

export interface User {
  id: string;
  username: string;
  role: UserRole;
}
