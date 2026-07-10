-- 기존 테이블이 이미 생성된 환경에서는 create table if not exists가 새 컬럼을 추가하지 않는다.
-- M3 이후 앱 계약에서 사용하는 색상 컬럼을 운영 DB에도 안전하게 보강한다.
alter table if exists public.goals
add column if not exists color text not null default '#4F46E5';

alter table if exists public.milestones
add column if not exists color text not null default '#F97316';

-- Supabase REST(PostgREST)가 새 컬럼을 바로 인식하도록 schema cache를 갱신한다.
notify pgrst, 'reload schema';
