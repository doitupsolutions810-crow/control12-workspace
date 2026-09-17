-- CONTROL12 Commercial v1 performance follow-up

create index if not exists idx_control12_audit_actor_user
  on public.control12_audit_events(actor_user_id);
create index if not exists idx_control12_deployments_release
  on public.control12_deployments(release_id);
create index if not exists idx_control12_memberships_user
  on public.control12_memberships(user_id);
create index if not exists idx_control12_orgs_owner_user
  on public.control12_organizations(owner_user_id);

-- Avoid duplicate SELECT policy evaluation: the existing FOR ALL policies already
-- cover reads for these tables.
drop policy if exists "control12 projects member read" on public.control12_projects;
drop policy if exists "control12 releases member read" on public.control12_releases;
drop policy if exists "control12 evidence member read" on public.control12_evidence;
drop policy if exists "control12 deployments member read" on public.control12_deployments;
