-- CONTROL12 Commercial v1 RLS hardening
-- Removes elevated public RPC semantics and keeps membership checks under caller RLS.

create or replace function public.control12_is_member(org_id uuid)
returns boolean
language sql
stable
security invoker
set search_path = public
as $$
  select exists (
    select 1
    from public.control12_memberships m
    where m.organization_id = org_id
      and m.user_id = (select auth.uid())
  );
$$;

drop policy if exists "control12 organizations member read" on public.control12_organizations;
create policy "control12 organizations member read"
on public.control12_organizations
for select
using (
  owner_user_id = (select auth.uid())
  or public.control12_is_member(id)
);

drop policy if exists "control12 organizations owner insert" on public.control12_organizations;
create policy "control12 organizations owner insert"
on public.control12_organizations
for insert
with check (owner_user_id = (select auth.uid()));

drop policy if exists "control12 memberships member read" on public.control12_memberships;
create policy "control12 memberships member read"
on public.control12_memberships
for select
using (user_id = (select auth.uid()));

drop policy if exists "control12 memberships self bootstrap" on public.control12_memberships;
create policy "control12 memberships self bootstrap"
on public.control12_memberships
for insert
with check (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.control12_organizations o
    where o.id = organization_id
      and o.owner_user_id = (select auth.uid())
  )
);
