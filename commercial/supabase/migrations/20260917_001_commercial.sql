create extension if not exists pgcrypto;

create table if not exists public.control12_organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$'),
  plan text not null default 'developer' check (plan in ('developer','team','business','enterprise')),
  owner_user_id uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);
create table if not exists public.control12_memberships (
  organization_id uuid not null references public.control12_organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','admin','member','viewer')),
  created_at timestamptz not null default now(),
  primary key (organization_id,user_id)
);
create table if not exists public.control12_projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.control12_organizations(id) on delete cascade,
  name text not null,
  repository_url text,
  default_branch text not null default 'main',
  created_at timestamptz not null default now(),
  unique (organization_id,name)
);
create table if not exists public.control12_releases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.control12_organizations(id) on delete cascade,
  project_id uuid not null references public.control12_projects(id) on delete cascade,
  version text not null,
  commit_sha text,
  artifact_sha256 text check (artifact_sha256 is null or artifact_sha256 ~ '^[0-9a-f]{64}$'),
  status text not null default 'draft',
  policy_status text not null default 'pending',
  created_at timestamptz not null default now(),
  verified_at timestamptz,
  unique (project_id,version)
);
create table if not exists public.control12_evidence (
  id uuid primary key default gen_random_uuid(),
  release_id uuid not null references public.control12_releases(id) on delete cascade,
  evidence_type text not null,
  source text not null,
  status text not null check (status in ('pass','fail','pending','informational')),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists public.control12_deployments (
  id uuid primary key default gen_random_uuid(),
  release_id uuid not null references public.control12_releases(id) on delete cascade,
  environment text not null,
  status text not null,
  target text,
  created_at timestamptz not null default now()
);
create table if not exists public.control12_usage_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.control12_organizations(id) on delete cascade,
  event_type text not null,
  quantity bigint not null default 1 check (quantity > 0),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists public.control12_audit_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.control12_organizations(id) on delete set null,
  actor_user_id uuid references auth.users(id) on delete set null,
  actor_label text,
  action text not null,
  resource_type text not null,
  resource_id text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_control12_projects_org on public.control12_projects(organization_id);
create index if not exists idx_control12_releases_org on public.control12_releases(organization_id);
create index if not exists idx_control12_releases_project on public.control12_releases(project_id);
create index if not exists idx_control12_evidence_release on public.control12_evidence(release_id);
create index if not exists idx_control12_usage_org on public.control12_usage_events(organization_id);
create index if not exists idx_control12_audit_org on public.control12_audit_events(organization_id);

alter table public.control12_organizations enable row level security;
alter table public.control12_memberships enable row level security;
alter table public.control12_projects enable row level security;
alter table public.control12_releases enable row level security;
alter table public.control12_evidence enable row level security;
alter table public.control12_deployments enable row level security;
alter table public.control12_usage_events enable row level security;
alter table public.control12_audit_events enable row level security;

create or replace function public.control12_is_member(org_id uuid)
returns boolean
language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.control12_memberships m where m.organization_id = org_id and m.user_id = auth.uid()); $$;

create policy "control12 organizations member read" on public.control12_organizations for select using (owner_user_id = auth.uid() or public.control12_is_member(id));
create policy "control12 organizations owner insert" on public.control12_organizations for insert with check (owner_user_id = auth.uid());
create policy "control12 memberships member read" on public.control12_memberships for select using (public.control12_is_member(organization_id));
create policy "control12 projects member read" on public.control12_projects for select using (public.control12_is_member(organization_id));
create policy "control12 projects member write" on public.control12_projects for all using (public.control12_is_member(organization_id)) with check (public.control12_is_member(organization_id));
create policy "control12 releases member read" on public.control12_releases for select using (public.control12_is_member(organization_id));
create policy "control12 releases member write" on public.control12_releases for all using (public.control12_is_member(organization_id)) with check (public.control12_is_member(organization_id));
create policy "control12 evidence member read" on public.control12_evidence for select using (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id)));
create policy "control12 evidence member write" on public.control12_evidence for all using (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id))) with check (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id)));
create policy "control12 deployments member read" on public.control12_deployments for select using (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id)));
create policy "control12 deployments member write" on public.control12_deployments for all using (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id))) with check (exists (select 1 from public.control12_releases r where r.id=release_id and public.control12_is_member(r.organization_id)));
create policy "control12 usage member read" on public.control12_usage_events for select using (public.control12_is_member(organization_id));
create policy "control12 audit member read" on public.control12_audit_events for select using (organization_id is not null and public.control12_is_member(organization_id));
