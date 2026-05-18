-- AI SecureWatch detections table.
-- Raw secrets must never be stored in this table. Store masked_value only.

create table if not exists public.detections (
  id uuid primary key default gen_random_uuid(),

  repo_full_name text not null,
  repo_owner text,
  repo_name text,
  branch text,
  commit_sha text,

  file_path text not null,
  line_number integer,

  secret_type text not null,
  masked_value text not null,
  detection_method text,
  entropy_score numeric,

  severity text not null,
  confidence_score numeric,
  ai_reasoning text,
  ai_recommendation text,

  status text not null default 'open',

  pusher_name text,
  pusher_email text,

  detected_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists idx_detections_repo
  on public.detections(repo_full_name);

create index if not exists idx_detections_severity
  on public.detections(severity);

create index if not exists idx_detections_status
  on public.detections(status);

create index if not exists idx_detections_detected_at
  on public.detections(detected_at);
