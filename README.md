# ManyDataCenter - Data Center Intelligence & Jobs Platform

ManyDataCenter is a platform designed to aggregate, analyze, and track information about global data centers (including locations, facilities, capacity, and specifications). 

The automated job listing ingestion pipeline is the initial starting point of this broader intelligence project.

---

## Current Architecture: Job Listings Ingestion

- **Extraction**: Paginated extraction of job listings matching "Data Center" from Amazon's internal JSON API.
- **Regex Parsing**: Extracts required years of experience and salary details from description and qualification texts.
- **Storage**: Updates a local CSV (`data-center-jobs/amazon_jobs.csv`) and upserts database records to Supabase (`amazon_jobs`).
- **Automation**: Runs daily via GitHub Actions.

## Extracted Fields

- `Job_ID`: Unique Amazon identifier.
- `Title`: Job title.
- `Location`: Job location.
- `Basic_Qualifications`: Raw qualifications text.
- `Description`: Raw description text.
- `Min_Years_Experience`: Minimum required years of experience.
- `Max_Years_Experience`: Maximum years of experience (if range is given).
- `Years_Experience_All`: All matched experience numbers.
- `Min_Salary`: Lower bound of salary range.
- `Max_Salary`: Upper bound of salary range.
- `Salary_Type`: Annual or hourly classification.
