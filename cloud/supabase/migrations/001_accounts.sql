create schema if not exists private;
create table public.members (
 id uuid primary key references auth.users(id) on delete cascade,
 share_measurements boolean not null default false,
 consent_version text, consent_at timestamptz,
 created_at timestamptz not null default now()
);
create table private.admins (user_id uuid primary key references auth.users(id) on delete cascade);
create table public.access_passes (
 user_id uuid primary key references auth.users(id) on delete cascade,
 expires_at timestamptz not null default now(), revoked boolean not null default false
);
create table public.measurements (
 id bigint generated always as identity primary key,
 user_id uuid not null references auth.users(id) on delete cascade,
 sample_key text not null check(sample_key ~ '^[0-9a-f]{64}$'),
 clone text not null check(clone in ('dragonbound','gunbound-world')),
 mobile text not null check(length(mobile) between 2 and 24),
 shot smallint not null check(shot between 0 and 2),
 sample jsonb not null,
 created_at timestamptz not null default now(), unique(user_id,sample_key)
);
create index measurement_groups on public.measurements(clone,mobile,shot,created_at);
create index measurement_quota on public.measurements(user_id,created_at);
create table public.calibration_candidates (
 id bigint generated always as identity primary key,
 clone text not null, mobile text not null, shot smallint not null,
 regime text not null, fit jsonb not null, contributors integer not null,
 source_count integer not null, evidence jsonb not null,
 status text not null default 'pending' check(status in ('pending','published','rejected')),
 fingerprint text not null unique, created_at timestamptz not null default now()
);
create table private.access_audit (
 request_id uuid primary key, actor uuid not null, target uuid not null,
 action text not null, months integer, created_at timestamptz not null default now()
);
create or replace function private.new_member() returns trigger language plpgsql security definer set search_path='' as $$
begin insert into public.members(id) values(new.id); return new; end $$;
create trigger dragonlab_new_member after insert on auth.users for each row execute function private.new_member();
insert into public.members(id) select id from auth.users on conflict do nothing;

alter table public.members enable row level security;
alter table public.access_passes enable row level security;
alter table public.measurements enable row level security;
alter table public.calibration_candidates enable row level security;
revoke all on public.members, public.access_passes, public.measurements, public.calibration_candidates from anon, authenticated;
grant select on public.members, public.access_passes to authenticated;
create policy own_member on public.members for select to authenticated using(id=auth.uid());
create policy own_pass on public.access_passes for select to authenticated using(user_id=auth.uid());
revoke all on schema private from public,anon,authenticated;

create or replace function public.is_admin() returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from private.admins where user_id=auth.uid())
$$;
create or replace function public.has_access() returns boolean language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and (public.is_admin() or exists(select 1 from public.access_passes where user_id=auth.uid() and not revoked and expires_at>now()))
$$;
create or replace function public.my_account() returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('user_id',m.id,'role',case when public.is_admin() then 'admin' else 'user' end,
 'email',(select email from auth.users where id=m.id),'server_now',now(),
 'expires_at',p.expires_at,'revoked',coalesce(p.revoked,false),'active',public.has_access(),
 'remaining_seconds',greatest(0,coalesce(extract(epoch from p.expires_at-now()),0)),
 'share_measurements',m.share_measurements,'consent_version',m.consent_version)
 from public.members m left join public.access_passes p on p.user_id=m.id where m.id=auth.uid()
$$;
create or replace function public.set_measurement_consent(enabled boolean, erase_existing boolean default false) returns void language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Debes iniciar sesión'; end if;
 perform 1 from public.members where id=auth.uid() for update;
 update public.members set share_measurements=enabled,consent_at=now(),consent_version=case when enabled then 'measurements-v1' else null end where id=auth.uid();
 if erase_existing then delete from public.measurements where user_id=auth.uid(); end if;
end $$;
create or replace function public.admin_users(page_offset integer default 0) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if not public.is_admin() then raise exception 'Solo administrador'; end if;
 return (select coalesce(jsonb_agg(t),'[]'::jsonb) from (select m.id,u.email,p.expires_at,coalesce(p.revoked,false) revoked,m.share_measurements,m.created_at,
 coalesce(not p.revoked and p.expires_at>now(),false) active from public.members m join auth.users u on u.id=m.id left join public.access_passes p on p.user_id=m.id order by m.created_at desc limit 50 offset greatest(0,page_offset)) t);
end $$;
create or replace function public.admin_grant(target uuid, months integer, request_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare end_date timestamptz; old_revoked boolean;
begin
 if not public.is_admin() then raise exception 'Solo administrador'; end if;
 if months not between 1 and 24 then raise exception 'Meses fuera de rango'; end if;
 insert into private.access_audit(request_id,actor,target,action,months) values(request_id,auth.uid(),target,'grant',months) on conflict do nothing;
 if not found then return jsonb_build_object('duplicate',true); end if;
 insert into public.access_passes(user_id) values(target) on conflict do nothing;
 select expires_at,revoked into end_date,old_revoked from public.access_passes where user_id=target for update;
 end_date:=(case when old_revoked then now() else greatest(now(),end_date) end)+make_interval(months=>months);
 update public.access_passes set expires_at=end_date,revoked=false where user_id=target;
 return jsonb_build_object('expires_at',end_date,'server_now',now());
end $$;
create or replace function public.admin_revoke(target uuid, request_id uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.is_admin() then raise exception 'Solo administrador'; end if;
 insert into private.access_audit(request_id,actor,target,action) values(request_id,auth.uid(),target,'revoke') on conflict do nothing;
 if found then update public.access_passes set revoked=true where user_id=target; end if;
end $$;
create or replace function public.ingest_measurements(batch jsonb) returns integer language plpgsql security definer set search_path='' as $$
declare entry jsonb; clean jsonb; k text; v numeric; inserted integer:=0; changed integer;
begin
 if not public.has_access() then raise exception 'Acceso vencido o suspendido'; end if;
 perform 1 from public.members where id=auth.uid() and share_measurements for update;
 if not found then raise exception 'Compartir mediciones no está activado'; end if;
 if jsonb_typeof(batch) is distinct from 'array' then raise exception 'Lote inválido'; end if;
 if jsonb_array_length(batch) not between 1 and 50 then raise exception 'Lote inválido'; end if;
 if (select count(*) from public.measurements where user_id=auth.uid() and created_at>now()-interval '1 day')+jsonb_array_length(batch)>1000 then raise exception 'Límite diario de mediciones'; end if;
 for entry in select value from jsonb_array_elements(batch) loop
  if entry->>'mobile' not in ('ARMOR','ICE','ADUKA','LIGHTNING','BIGFOOT','JD','ASATE','NAK','TRICO','MAGE','TURTLE','BOOMER','GRUB','RANDOMIZER','RAON','FROG','KALSIDDON','FOX','ELECTRICO','DRAGON') then raise exception 'Carro inválido'; end if;
  if entry->>'source' is distinct from 'native-shot-start' then raise exception 'Se requiere medición nativa'; end if;
  clean:='{}'::jsonb;
  foreach k in array array['power','vx','vy','ax','ay','wind','wind_angle'] loop
   if jsonb_typeof(entry->k)<>'number' or entry->k is null then raise exception 'Medición inválida: %',k; end if;
   v:=(entry->>k)::numeric;
   if abs(v)>10000 then raise exception 'Medición fuera de rango'; end if;
   clean:=clean||jsonb_build_object(k,v);
  end loop;
  if (clean->>'power')::numeric not between 1 and 400 or (clean->>'wind')::numeric not between 0 and 100 or (clean->>'wind_angle')::numeric not between 0 and 360 then raise exception 'Fuerza o viento fuera de rango'; end if;
  insert into public.measurements(user_id,sample_key,clone,mobile,shot,sample) values(auth.uid(),entry->>'sample_key',entry->>'clone',entry->>'mobile',(entry->>'shot')::smallint,clean) on conflict do nothing;
  get diagnostics changed=row_count;inserted:=inserted+changed;
 end loop;
 return inserted;
end $$;
create or replace function public.published_calibrations() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not public.has_access() then raise exception 'Acceso vencido o suspendido'; end if;
 return (select coalesce(jsonb_agg(t),'[]'::jsonb) from (select distinct on(clone,mobile,shot,regime) id,clone,mobile,shot,regime,fit,created_at from public.calibration_candidates where status='published' order by clone,mobile,shot,regime,created_at desc) t);
end $$;
create or replace function public.admin_candidates() returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if not public.is_admin() then raise exception 'Solo administrador'; end if;
 return (select coalesce(jsonb_agg(t),'[]'::jsonb) from(select id,clone,mobile,shot,regime,fit,contributors,source_count,evidence,status from public.calibration_candidates order by created_at desc limit 50)t);
end $$;
create or replace function public.admin_publish(candidate bigint, approved boolean) returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.is_admin() then raise exception 'Solo administrador'; end if;
 update public.calibration_candidates set status=case when approved then 'published' else 'rejected' end where id=candidate and status='pending';
end $$;
-- PostgreSQL grants EXECUTE to PUBLIC by default: revoke it explicitly.
revoke execute on function public.is_admin(),public.has_access(),public.my_account(),public.set_measurement_consent(boolean,boolean),public.admin_users(integer),public.admin_grant(uuid,integer,uuid),public.admin_revoke(uuid,uuid),public.ingest_measurements(jsonb),public.published_calibrations(),public.admin_candidates(),public.admin_publish(bigint,boolean) from public,anon;
grant execute on function public.is_admin(),public.has_access(),public.my_account(),public.set_measurement_consent(boolean,boolean),public.admin_users(integer),public.admin_grant(uuid,integer,uuid),public.admin_revoke(uuid,uuid),public.ingest_measurements(jsonb),public.published_calibrations(),public.admin_candidates(),public.admin_publish(bigint,boolean) to authenticated;
grant all on public.measurements,public.calibration_candidates to service_role;
grant usage,select on all sequences in schema public to service_role;
