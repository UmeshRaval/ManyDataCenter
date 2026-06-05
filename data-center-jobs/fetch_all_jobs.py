import os
import requests
import pandas as pd
import time
import re
from bs4 import BeautifulSoup

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
            r = requests.get(url, params=params, headers=headers, timeout=10)
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
        title = job.get("title", "")
        title_lower = title.lower() if title else ""
        if 'data center' not in title_lower and 'datacenter' not in title_lower and 'critical' not in title_lower:
            continue
            
        basic_qual = job.get("basic_qualifications", "") or ""
        desc = job.get("description", "") or ""
        
        min_years, max_years, years_list = extract_years_of_experience(basic_qual)
        min_salary, max_salary, salary_type = extract_salary_range(desc)
        
        processed.append({
            "job_id": f"aws-{job.get('id_icims')}",
            "operator_id": "aws",
            "title": title,
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
            r = requests.post(search_url, json=payload, headers=headers, timeout=10)
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
        title = job.get("title", "")
        title_lower = title.lower() if title else ""
        if 'data center' not in title_lower and 'datacenter' not in title_lower and 'critical' not in title_lower:
            continue
            
        location = job.get("locationsText")
        
        print(f"  [{idx+1}/{len(jobs_summary)}] Fetching details: {title} ({location})...")
        desc = ""
        job_req_id = job.get("bulletFields", [None])[0] if job.get("bulletFields") else None
        
        try:
            detail_r = requests.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
# 2.1 Microsoft Azure Scraper
# ----------------------------------------
def fetch_azure_jobs(limit=None):
    print("\n--- Fetching AZURE Jobs via Microsoft Careers API ---")
    search_url = "https://apply.careers.microsoft.com/api/pcsx/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    jobs_list = []
    page = 1
    page_size = 10
    
    while True:
        params = {
            "domain": "microsoft.com",
            "query": "Data Center",
            "location": "",
            "page": page
        }
        try:
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json().get('data', {})
        except Exception as e:
            print(f"Error fetching Azure search at start {start}: {e}")
            break
            
        positions = data.get('positions', [])
        if not positions:
            break
            
        jobs_list.extend(positions)
        total = data.get('count', 0)
        print(f"AZURE: Found {len(jobs_list)} / {total} listings...")
        
        if limit and len(jobs_list) >= limit:
            jobs_list = jobs_list[:limit]
            break
            
        if len(positions) < page_size or page * page_size >= total:
            break
            
        page += 1
        time.sleep(0.5)
        
    processed = []
    for idx, pos in enumerate(jobs_list):
        pos_id = pos.get('id')
        title = pos.get('name')
        locations_list = pos.get('standardizedLocations', []) or pos.get('locations', []) or []
        location = ", ".join(locations_list) if locations_list else None
        
        print(f"  [{idx+1}/{len(jobs_list)}] Fetching Azure details for: {title}...")
        desc = ""
        try:
            detail_url = "https://apply.careers.microsoft.com/api/pcsx/position_details"
            detail_params = {
                "position_id": pos_id,
                "domain": "microsoft.com",
                "hl": "en"
            }
            r_det = requests.get(detail_url, params=detail_params, headers=headers, timeout=10)
            if r_det.status_code == 200:
                job_info = r_det.json().get('data', {})
                desc = job_info.get('jobDescription', "")
        except Exception as e:
            print(f"    Error fetching details: {e}")
            
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        processed.append({
            "job_id": f"azure-{pos_id}",
            "operator_id": "azure",
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
        time.sleep(0.5)
        
    return processed

# ----------------------------------------
# 2.2 Digital Realty Scraper
# ----------------------------------------
def fetch_digital_realty_jobs(limit=None):
    print("\n--- Fetching DIGITAL REALTY Jobs via Oracle HCM API ---")
    url = "https://hdep.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    params = {
        'onlyData': 'true',
        'expand': 'requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields',
        'finder': 'findReqs;siteNumber=CX,facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,limit=100,keyword="Data Center",sortBy=RELEVANCY'
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data.get('items', [])
        requisitions = items[0].get('requisitionList', []) if items else []
    except Exception as e:
        print(f"Error fetching Digital Realty search: {e}")
        return []
        
    if limit:
        requisitions = requisitions[:limit]
        
    print(f"DIGITAL REALTY: Found {len(requisitions)} listings...")
    processed = []
    
    for idx, req in enumerate(requisitions):
        req_id = req.get('Id')
        title = req.get('Title')
        location = req.get('PrimaryLocation')
        
        print(f"  [{idx+1}/{len(requisitions)}] Fetching Digital Realty details for: {title}...")
        desc = ""
        try:
            preview_url = f"https://hdep.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/requisitions/preview/{req_id}"
            r_prev = requests.get(preview_url, headers=headers, timeout=10)
            if r_prev.status_code == 200:
                soup = BeautifulSoup(r_prev.text, 'html.parser')
                meta = soup.find('meta', property='og:description')
                if meta:
                    desc = meta.get('content', '')
        except Exception as e:
            print(f"    Error fetching preview details: {e}")
            
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        processed.append({
            "job_id": f"digital-realty-{req_id}",
            "operator_id": "digital-realty",
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
        time.sleep(0.5)
        
    return processed

# ----------------------------------------
# 2.3 EdgeConneX Scraper
# ----------------------------------------
def fetch_edgeconnex_jobs(limit=None):
    print("\n--- Fetching EDGECONNEX Jobs via Greenhouse API ---")
    url = "https://boards-api.greenhouse.io/v1/boards/edgeconnex/jobs"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    params = {
        "content": "true"
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        jobs = r.json().get('jobs', [])
    except Exception as e:
        print(f"Error fetching EdgeConneX jobs: {e}")
        return []
        
    dc_jobs = []
    for job in jobs:
        title = job.get('title', '')
        if 'data center' in title.lower() or 'datacenter' in title.lower() or 'critical' in title.lower() or 'facility' in title.lower():
            dc_jobs.append(job)
            
    if limit:
        dc_jobs = dc_jobs[:limit]
        
    print(f"EDGECONNEX: Found {len(dc_jobs)} matching listings...")
    processed = []
    
    for job in dc_jobs:
        job_id = job.get('id')
        title = job.get('title')
        location = job.get('location', {}).get('name')
        desc = job.get('content', '')
        
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        processed.append({
            "job_id": f"edgeconnex-{job_id}",
            "operator_id": "edgeconnex",
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
        
    return processed

# ----------------------------------------
# 2.4 Compass Datacenters Scraper
# ----------------------------------------
def fetch_compass_jobs(limit=None):
    print("\n--- Fetching COMPASS Jobs via Breezy HR API ---")
    url = "https://compass-datacenters.breezy.hr/json"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        jobs = r.json()
    except Exception as e:
        print(f"Error fetching Compass jobs: {e}")
        return []
        
    dc_jobs = []
    for job in jobs:
        title = job.get('name', '')
        if 'data center' in title.lower() or 'datacenter' in title.lower() or 'operations' in title.lower() or 'facility' in title.lower() or 'engineer' in title.lower():
            dc_jobs.append(job)
            
    if limit:
        dc_jobs = dc_jobs[:limit]
        
    print(f"COMPASS: Found {len(dc_jobs)} matching listings...")
    processed = []
    
    for idx, job in enumerate(dc_jobs):
        job_id = job.get('id')
        title = job.get('name')
        job_url = job.get('url')
        loc_info = job.get('location', {})
        location = f"{loc_info.get('city', '')}, {loc_info.get('state', {}).get('name', '')}, {loc_info.get('country', {}).get('name', '')}".strip(", ")
        
        print(f"  [{idx+1}/{len(dc_jobs)}] Fetching Compass details for: {title}...")
        desc = ""
        try:
            r_det = requests.get(job_url, headers=headers, timeout=10)
            if r_det.status_code == 200:
                soup = BeautifulSoup(r_det.text, 'html.parser')
                div = soup.find('div', class_='description') or soup.find('div', itemprop='description')
                if div:
                    desc = str(div)
        except Exception as e:
            print(f"    Error fetching details: {e}")
            
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        processed.append({
            "job_id": f"compass-{job_id}",
            "operator_id": "compass",
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
        time.sleep(0.5)
        
    return processed

# ----------------------------------------
# 2.5 Sabey Data Centers Scraper
# ----------------------------------------
def fetch_sabey_jobs(limit=None):
    print("\n--- Fetching SABEY Jobs by HTML Scraping ---")
    url = "https://sabeydatacenters.com/about/careers"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching Sabey careers: {e}")
        return []
        
    job_rows = []
    for row in soup.find_all('div', class_='flex flex-wrap'):
        h1 = row.find('h1')
        a = row.find('a', href=lambda h: h and 'icims.com' in h)
        if h1 and a:
            title = h1.text.strip()
            link = a['href']
            
            loc_p = row.find('p', class_='text-gray-600')
            location = loc_p.text.strip() if loc_p else None
            
            desc_div = row.find('div', class_='rich-text')
            description = desc_div.text.strip() if desc_div else ""
            
            job_rows.append({
                "title": title,
                "location": location,
                "url": link,
                "description": description
            })
            
    if limit:
        job_rows = job_rows[:limit]
        
    print(f"SABEY: Found {len(job_rows)} listings...")
    processed = []
    
    for job in job_rows:
        title = job["title"]
        location = job["location"]
        link = job["url"]
        desc = job["description"]
        
        match = re.search(r'/jobs/(\d+)/', link)
        job_id = match.group(1) if match else str(hash(link))
        
        clean_text = re.sub(r'<[^>]*>', ' ', desc)
        min_years, max_years, years_list = extract_years_of_experience(clean_text)
        min_salary, max_salary, salary_type = extract_salary_range(clean_text)
        
        processed.append({
            "job_id": f"sabey-{job_id}",
            "operator_id": "sabey",
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
            response = requests.post(url, json=cleaned_chunk, headers=headers, timeout=10)
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
    
    # 1. Fetch AWS jobs (No limit to fetch all available listings)
    try:
        aws_jobs = fetch_aws_jobs(limit=None)
        all_jobs.extend(aws_jobs)
    except Exception as e:
        print(f"Failed fetching AWS jobs: {e}")
        
    # Workday configurations for operators (No limit to fetch all listings)
    workday_configs = [
        {
            "operator_id": "equinix",
            "base_url": "https://equinix.wd1.myworkdayjobs.com",
            "tenant": "equinix",
            "site_id": "External",
            "limit": None
        },
        {
            "operator_id": "cyrusone",
            "base_url": "https://cyrusone.wd1.myworkdayjobs.com",
            "tenant": "cyrusone",
            "site_id": "CyrusOneCareerPortal",
            "limit": None
        },
        {
            "operator_id": "qts",
            "base_url": "https://qtsdatacenters.wd5.myworkdayjobs.com",
            "tenant": "qtsdatacenters",
            "site_id": "QTS",
            "limit": None
        },
        {
            "operator_id": "iron-mountain",
            "base_url": "https://ironmountain.wd5.myworkdayjobs.com",
            "tenant": "ironmountain",
            "site_id": "iron-mountain-jobs",
            "limit": None
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
            
    # 3. Fetch from additional operators
    additional_scrapers = [
        ("azure", fetch_azure_jobs),
        ("digital-realty", fetch_digital_realty_jobs),
        ("edgeconnex", fetch_edgeconnex_jobs),
        ("compass", fetch_compass_jobs),
        ("sabey", fetch_sabey_jobs)
    ]
    for name, scraper_func in additional_scrapers:
        try:
            new_jobs = scraper_func(limit=None)
            all_jobs.extend(new_jobs)
        except Exception as e:
            print(f"Failed fetching jobs for {name}: {e}")
            
    if not all_jobs:
        print("No jobs fetched.")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(all_jobs)
    
    # Deduplicate locally by job_id (keeping the first occurrence)
    if not df.empty:
        df.drop_duplicates(subset=["job_id"], keep="first", inplace=True)
        
    # Save combined results locally
    output_path = os.path.join(os.path.dirname(__file__), "data_center_jobs.csv")
    df.to_csv(output_path, index=False)
    print(f"\nPipeline finished. Saved {len(df)} total jobs locally to {output_path}")
    
    # Upload to Supabase
    upload_to_supabase(df.to_dict(orient="records"))
    
    # Print summary statistics
    print("\nDataFrame Shape:", df.shape)
    print("Jobs by Operator:")
    print(df["operator_id"].value_counts())
    print("\nJobs with parsed experience requirements:", df["min_years_experience"].notnull().sum())
    print("Jobs with parsed salary range info:", df["min_salary"].notnull().sum())

if __name__ == "__main__":
    main()
