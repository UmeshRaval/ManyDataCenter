# ManyDataCenter - Data Center Intelligence & Jobs Platform

ManyDataCenter is a project designed to aggregate, analyze, and track information about global data centers (including locations, facilities, capacity, and specifications).

The platform currently includes:
1. **Data Center Operators**: Seed data for major hyperscalers, wholesale providers, and colocation operators.
2. **Data Center Jobs**: Automated pipeline compiling data-center-specific job openings across all tracked operators.

---

## 1. Data Center Operators

The script `data-center-jobs/add_operators.py` compiles and updates a list of major industry players.

- **Local Storage**: Saved as a CSV at `data-center-jobs/operators.csv`.
- **Database Storage**: Upserts to the Supabase database.

## 2. Data Center Jobs

The script `data-center-jobs/fetch_all_jobs.py` fetches job listings and maps them to a unified database table. Currently, it aggregates listings from Amazon (AWS), Microsoft Azure, Equinix, CyrusOne, QTS, Iron Mountain, Digital Realty, EdgeConneX, Compass Datacenters, and Sabey Data Centers. 

The pipeline features:
- **Title Filtering**: Accurately extracts actual data center/critical environment roles rather than generic cloud engineering jobs.
- **NLP Extraction**: Automatically parses years of experience required and salary bands directly from raw job descriptions.
- **Local Storage**: Saved as a CSV at `data-center-jobs/data_center_jobs.csv`.
- **Database Storage**: Upserts to the Supabase database.
- **Automation**: Designed to run cleanly as an automated daily workflow.

---

## Local Setup & Execution

If you want to run the pipelines locally, navigate to the `data-center-jobs` directory and ensure you have installed the requirements (e.g., `requests`, `pandas`, `beautifulsoup4`).

### Environment Variables
To enable automatic database syncing, set the following environment variables in your terminal:
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase API key (Service Role key recommended for bulk upserts).

*Note: If these environment variables are omitted, the scripts will simply skip the upload phase and save the results cleanly to local CSV files.*

### Running the Scripts

**1. Seed Operators:**
```bash
python data-center-jobs/add_operators.py
```

**2. Fetch All Jobs:**
```bash
python data-center-jobs/fetch_all_jobs.py
```


**3. Manual Supabase Sync (Optional):**
If you already have a generated `data_center_jobs.csv` and just want to push it to the database without re-scraping:
```bash
python data-center-jobs/upload_to_supabase.py
```
### Live Dashboard

Check out my Google Data Studio dashboard to visualize the data in realtime. [Data Center Jobs](https://datastudio.google.com/reporting/1b2a6348-1bb7-41a7-ba46-7422342fcf31)
