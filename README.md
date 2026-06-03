# ManyDataCenter - Data Center Intelligence & Jobs Platform

ManyDataCenter is a project designed to aggregate, analyze, and track information about global data centers (including locations, facilities, capacity, and specifications).

The platform currently includes:
1. **Data Center Operators**: Seed data for major hyperscalers, wholesale providers, and colocation operators.
2. **Job Listings Ingestion**: Automated daily pipeline tracking data-center-specific job openings.

---

## 1. Data Center Operators

The script `data-center-jobs/add_operators.py` compiles and updates a list of major industry players.

- **Local Storage**: Saved as a CSV at `data-center-jobs/operators.csv`.
- **Database Storage**: Upserts to the Supabase `data_center_operators` table.

### Supabase Table Schema
```sql
create table if not exists public.data_center_operators (
    id text primary key,
    name text not null,
    code text unique not null,
    website text,
    headquarters text,
    operator_type text,
    description text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.data_center_operators enable row level security;

-- Allow public read access
create policy "Allow public read access to operators"
on public.data_center_operators
for select
to public
using (true);
```

---

## 2. Job Listings Ingestion

The script `data-center-jobs/amazon_fetch.py` fetches job listings matching "Data Center".

- **Local Storage**: Saved as a CSV at `data-center-jobs/amazon_jobs.csv`.
- **Database Storage**: Upserts to the Supabase `amazon_jobs` table.
- **Automation**: Runs daily via GitHub Actions.

### Supabase Table Schema
```sql
create table if not exists public.amazon_jobs (
    job_id text primary key,
    title text,
    location text,
    basic_qualifications text,
    description text,
    min_years_experience integer,
    max_years_experience integer,
    years_experience_all integer[],
    min_salary numeric,
    max_salary numeric,
    salary_type text,
    fetched_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.amazon_jobs enable row level security;

-- Allow public read access
create policy "Allow public read access to jobs"
on public.amazon_jobs
for select
to public
using (true);
```
