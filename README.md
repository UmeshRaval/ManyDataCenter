# ManyDataCenter - Jobs Pipeline

An automated data pipeline that fetches "Data Center" jobs from the Amazon Jobs API, extracts structured fields using regular expressions, and upserts them to a Supabase database.

## Architecture

- **Extraction**: Paginated extraction from Amazon's internal JSON endpoint in batches of 100.
- **Regex Parsing**: Extracts required years of experience and salary range details.
- **Storage**: Updates a local CSV (`data-center-jobs/amazon_jobs.csv`) and upserts to a Supabase database (`amazon_jobs`).
- **Automation**: Executed daily via GitHub Actions.

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
