import os
import requests
import pandas as pd
import time
import re

# Regex patterns for parsing qualifications and descriptions
YOEX_PATTERN = re.compile(r'(?i)\b(\d+)(?:\s*(?:-|to)\s*(\d+))?\+?\s*years?\b')
SALARY_PATTERN = re.compile(
    r'(?i)(?:salary|pay|compensation)(?:\s*(?:range|rate|of|is|band|level|information))*\s*:?\s*\$?([0-9,]+(?:\.[0-9]+)?)(?:\s*(?:/year|/yr|/hour|/hr|/h))?'
    r'\s*(?:-|to)\s*'
    r'\$?([0-9,]+(?:\.[0-9]+)?)(?:\s*(?:/year|/yr|/hour|/hr|/h))?'
)

def extract_years_of_experience(text):
    if not text:
        return None, None, []
    matches = YOEX_PATTERN.findall(text)
    if not matches:
        return None, None, []
    
    years_list = []
    min_years = None
    max_years = None
    
    for min_y, max_y in matches:
        val_min = int(min_y)
        years_list.append(val_min)
        if max_y:
            val_max = int(max_y)
            years_list.append(val_max)
            if max_years is None or val_max > max_years:
                max_years = val_max
        if min_years is None or val_min > min_years:
            min_years = val_min
            
    return min_years, max_years, years_list

def extract_salary_range(text):
    if not text:
        return None, None, None
    match = SALARY_PATTERN.search(text)
    if not match:
        return None, None, None
        
    min_sal = float(match.group(1).replace(',', ''))
    max_sal = float(match.group(2).replace(',', ''))
    
    salary_type = 'annual'
    matched_text = match.group(0).lower()
    if 'hour' in matched_text or 'hr' in matched_text or 'h' in matched_text or min_sal < 500:
        salary_type = 'hourly'
        
    return min_sal, max_sal, salary_type

# ----------------------------------------
# 1. AWS Scraper
# ----------------------------------------
def fetch_aws_jobs(limit=100):
    url = "https://www.amazon.jobs/en/search.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Encoding": "gzip, deflate"
    }
    
    jobs_list = []
    offset = 0
    result_limit = 100
    
    print("\n--- Fetching AWS Jobs ---")
    while True:
        params = {
            "base_query": "Data Center",
            "result_limit": result_limit,
            "offset": offset,
            "sort": "recent"
        }
        try:
            r = requests.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Error fetching AWS at offset {offset}: {e}")
            break
            
        jobs = data.get('jobs', [])
        if not jobs:
            break
            
        jobs_list.extend(jobs)
        total = data.get('hits', 0)
        print(f"AWS: Fetched {len(jobs_list)} / {total} jobs...")
        
        if limit and len(jobs_list) >= limit:
            jobs_list = jobs_list[:limit]
            break
        if len(jobs) < result_limit or offset + len(jobs) >= total:
            break
        offset += len(jobs)
        time.sleep(0.5)
        
    processed = []
    for job in jobs_list:
        basic_qual = job.get("basic_qualifications", "") or ""
        desc = job.get("description", "") or ""
        
        min_years, max_years, years_list = extract_years_of_experience(basic_qual)
        min_salary, max_salary, salary_type = extract_salary_range(desc)
        
        processed.append({
            "job_id": f"aws-{job.get('id_icims')}",
            "operator_id": "aws",
            "title": job.get("title"),
            "location": job.get("location"),
            "basic_qualifications": basic_qual,
            "description": desc,
            "min_years_experience": min_years,
            "max_years_experience": max_years,
            "years_experience_all": years_list,
            "min_salary": min_salary,
            "max_salary": max_salary,
            "salary_type": salary_type
        })
    return processed

# ----------------------------------------
# 2. Generic Workday Scraper
# ----------------------------------------
def fetch_workday_jobs(operator_id, base_url, tenant, site_id, limit=50):
    """
    Fetches job listings from a Workday instance and scrapes detail pages for descriptions.
    """
    print(f"\n--- Fetching {operator_id.upper()} Jobs via Workday ---")
    
    search_url = f"{base_url}/wday/cxs/{tenant}/{site_id}/jobs"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    jobs_summary = []
    offset = 0
    page_limit = 20
    
    while True:
        payload = {
            "appliedFacets": {},
            "limit": page_limit,
            "offset": offset,
            "searchText": "Data Center"
        }
        try:
            r = requests.post(search_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Error calling Workday search API for {operator_id}: {e}")
            break
            
        postings = data.get('jobPostings', [])
        if not postings:
            break
            
        jobs_summary.extend(postings)
        total = data.get('total', 0)
        print(f"{operator_id.upper()}: Found {len(jobs_summary)} / {total} listings...")
        
        if limit and len(jobs_summary) >= limit:
            jobs_summary = jobs_summary[:limit]
            break
        if len(postings) < page_limit or offset + len(postings) >= total:
            break
        offset += len(postings)
        time.sleep(0.5)
        
    # Query details for each job posting to retrieve full descriptions
    processed = []
    for idx, job in enumerate(jobs_summary):
        path = job.get("externalPath")
        if not path:
            continue
            
        detail_url = f"{base_url}/wday/cxs/{tenant}/{site_id}{path}"
        title = job.get("title")
        location = job.get("locationsText")
        
        print(f"  [{idx+1}/{len(jobs_summary)}] Fetching details: {title} ({location})...")
        desc = ""
        job_req_id = job.get("bulletFields", [None])[0] if job.get("bulletFields") else None
        
        try:
            detail_r = requests.get(detail_url, headers={"User-Agent": "Mozilla/5.0"})
            if detail_r.status_code == 200:
                info = detail_r.json().get("jobPostingInfo", {})
                desc = info.get("jobDescription", "")
                if not job_req_id:
                    job_req_id = info.get("jobReqId") or info.get("jobPostingId")
        except Exception as e:
            print(f"  Error fetching job detail: {e}")
            
        # Clean HTML tags for regex matching (optional, but regex works either way)
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        # Use jobReqId or construct a fallback ID
        raw_id = job_req_id if job_req_id else str(hash(path))
        
        processed.append({
            "job_id": f"{operator_id}-{raw_id}",
            "operator_id": operator_id,
            "title": title,
            "location": location,
            "basic_qualifications": None,
            "description": desc,
            "min_years_experience": min_years,
            "max_years_experience": max_years,
            "years_experience_all": years_list,
            "min_salary": min_salary,
            "max_salary": max_salary,
            "salary_type": salary_type
        })
        time.sleep(0.5) # Polite delay
        
    return processed

# ----------------------------------------
# 3. Supabase Upload
# ----------------------------------------
def upload_to_supabase(records):
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("\nNote: SUPABASE_URL or SUPABASE_KEY environment variables not set. Skipping Supabase upload.")
        return
        
    chunk_size = 100
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    url = f"{supabase_url.rstrip('/')}/rest/v1/data_center_jobs"
    
    print(f"\nUploading {len(records)} jobs to Supabase...")
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i+chunk_size]
        # Clean records to match DB column types exactly
        cleaned_chunk = []
        for r in chunk:
            cleaned_chunk.append({
                "job_id": r["job_id"],
                "operator_id": r["operator_id"],
                "title": r["title"] if pd.notnull(r["title"]) else None,
                "location": r["location"] if pd.notnull(r["location"]) else None,
                "basic_qualifications": r["basic_qualifications"] if pd.notnull(r["basic_qualifications"]) else None,
                "description": r["description"] if pd.notnull(r["description"]) else None,
                "min_years_experience": int(r["min_years_experience"]) if pd.notnull(r["min_years_experience"]) else None,
                "max_years_experience": int(r["max_years_experience"]) if pd.notnull(r["max_years_experience"]) else None,
                "years_experience_all": r["years_experience_all"] if isinstance(r["years_experience_all"], list) else None,
                "min_salary": float(r["min_salary"]) if pd.notnull(r["min_salary"]) else None,
                "max_salary": float(r["max_salary"]) if pd.notnull(r["max_salary"]) else None,
                "salary_type": r["salary_type"] if pd.notnull(r["salary_type"]) else None
            })
        try:
            response = requests.post(url, json=cleaned_chunk, headers=headers)
            response.raise_for_status()
            print(f"Successfully uploaded chunk {i//chunk_size + 1} ({len(cleaned_chunk)} jobs)...")
        except Exception as e:
            print(f"Error uploading chunk {i//chunk_size + 1} to Supabase: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("Response detail:", e.response.text)

# ----------------------------------------
# Main Orchestrator
# ----------------------------------------
def main():
    all_jobs = []
    
    # 1. Fetch AWS jobs (Limit to 100 for safety, adjust as needed)
    try:
        aws_jobs = fetch_aws_jobs(limit=100)
        all_jobs.extend(aws_jobs)
    except Exception as e:
        print(f"Failed fetching AWS jobs: {e}")
        
    # Workday configurations for operators
    workday_configs = [
        {
            "operator_id": "equinix",
            "base_url": "https://equinix.wd1.myworkdayjobs.com",
            "tenant": "equinix",
            "site_id": "External",
            "limit": 50
        },
        {
            "operator_id": "cyrusone",
            "base_url": "https://cyrusone.wd1.myworkdayjobs.com",
            "tenant": "cyrusone",
            "site_id": "CyrusOneCareerPortal",
            "limit": 50
        },
        {
            "operator_id": "qts",
            "base_url": "https://qtsdatacenters.wd5.myworkdayjobs.com",
            "tenant": "qtsdatacenters",
            "site_id": "QTS",
            "limit": 50
        }
    ]
    
    # 2. Fetch from each Workday operator
    for cfg in workday_configs:
        try:
            wd_jobs = fetch_workday_jobs(
                operator_id=cfg["operator_id"],
                base_url=cfg["base_url"],
                tenant=cfg["tenant"],
                site_id=cfg["site_id"],
                limit=cfg["limit"]
            )
            all_jobs.extend(wd_jobs)
        except Exception as e:
            print(f"Failed fetching jobs for {cfg['operator_id']}: {e}")
            
    if not all_jobs:
        print("No jobs fetched.")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(all_jobs)
    
    # Save combined results locally
    output_path = os.path.join(os.path.dirname(__file__), "data_center_jobs.csv")
    df.to_csv(output_path, index=False)
    print(f"\nPipeline finished. Saved {len(df)} total jobs locally to {output_path}")
    
    # Upload to Supabase
    upload_to_supabase(all_jobs)
    
    # Print summary statistics
    print("\nDataFrame Shape:", df.shape)
    print("Jobs by Operator:")
    print(df["operator_id"].value_counts())
    print("\nJobs with parsed experience requirements:", df["min_years_experience"].notnull().sum())
    print("Jobs with parsed salary range info:", df["min_salary"].notnull().sum())

if __name__ == "__main__":
    main()
