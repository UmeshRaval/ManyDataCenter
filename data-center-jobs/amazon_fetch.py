import requests
import pandas as pd
import time
import re
import os

def extract_years_of_experience(qualifications_text):
    """
    Extracts years of experience requirements from qualifications text using Regex.
    Returns:
        - min_years: The maximum of the minimum years required (as overall requirement bottleneck).
        - max_years: The maximum years if a range is specified (e.g. 5 for "3-5 years").
        - years_list: A list of all matched years of experience numbers.
    """
    if not qualifications_text:
        return None, None, []
    
    # Matches patterns like "2+ years", "3-5 years", "3 to 5 years", "1 year"
    pattern = re.compile(r'(?i)\b(\d+)(?:\s*(?:-|to)\s*(\d+))?\+?\s*years?\b')
    matches = pattern.findall(qualifications_text)
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

def extract_salary_range(description_text):
    """
    Extracts salary bands (ranges) from job descriptions using Regex.
    Returns:
        - min_salary: The lower bound of the salary range.
        - max_salary: The upper bound of the salary range.
        - salary_type: 'annual' or 'hourly' depending on context/value.
    """
    if not description_text:
        return None, None, None
        
    pattern = re.compile(
        r'(?i)(?:salary|pay|compensation)(?:\s*(?:range|rate|of|is|band|level|information))*\s*:?\s*\$?([0-9,]+(?:\.[0-9]+)?)(?:\s*(?:/year|/yr|/hour|/hr|/h))?'
        r'\s*(?:-|to)\s*'
        r'\$?([0-9,]+(?:\.[0-9]+)?)(?:\s*(?:/year|/yr|/hour|/hr|/h))?'
    )
    match = pattern.search(description_text)
    if not match:
        return None, None, None
        
    min_sal = float(match.group(1).replace(',', ''))
    max_sal = float(match.group(2).replace(',', ''))
    
    salary_type = 'annual'
    matched_text = match.group(0).lower()
    if 'hour' in matched_text or 'hr' in matched_text or 'h' in matched_text or min_sal < 500:
        salary_type = 'hourly'
        
    return min_sal, max_sal, salary_type

def fetch_amazon_dc_jobs(max_results=None):
    """
    Fetches Amazon jobs matching 'Data Center' using the internal JSON search API,
    handling pagination automatically.
    """
    url = "https://www.amazon.jobs/en/search.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Encoding": "gzip, deflate"
    }
    
    jobs_list = []
    offset = 0
    result_limit = 100
    
    print("Starting fetch from Amazon Jobs API...")
    
    while True:
        params = {
            "base_query": "Data Center",
            "result_limit": result_limit,
            "offset": offset,
            "sort": "recent"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching data at offset {offset}: {e}")
            break
            
        jobs = data.get('jobs', [])
        if not jobs:
            break
            
        jobs_list.extend(jobs)
        total_hits = data.get('hits', 0)
        print(f"Fetched {len(jobs_list)} / {total_hits} jobs...")
        
        if max_results and len(jobs_list) >= max_results:
            jobs_list = jobs_list[:max_results]
            break
            
        if len(jobs) < result_limit or offset + len(jobs) >= total_hits:
            break
            
        offset += len(jobs)
        time.sleep(0.5) # Polite delay to avoid rate limiting
        
    processed_jobs = []
    for job in jobs_list:
        basic_qual = job.get("basic_qualifications", "") or ""
        desc = job.get("description", "") or ""
        
        min_years, max_years, years_list = extract_years_of_experience(basic_qual)
        min_salary, max_salary, salary_type = extract_salary_range(desc)
        
        processed_jobs.append({
            "Job_ID": job.get("id_icims"),
            "Title": job.get("title"),
            "Location": job.get("location"),
            "Basic_Qualifications": basic_qual,
            "Description": desc,
            "Min_Years_Experience": min_years,
            "Max_Years_Experience": max_years,
            "Years_Experience_All": years_list,
            "Min_Salary": min_salary,
            "Max_Salary": max_salary,
            "Salary_Type": salary_type
        })
        
    return pd.DataFrame(processed_jobs)

if __name__ == "__main__":
    # Fetching a larger batch to demonstrate extraction (e.g., 500 jobs)
    # Set max_results to None to fetch all available jobs.
    df = fetch_amazon_dc_jobs(max_results=500)
    
    # Save the pipeline results to CSV
    output_path = os.path.join(os.path.dirname(__file__), "amazon_jobs.csv")
    df.to_csv(output_path, index=False)
    print(f"\nPipeline finished. Saved {len(df)} jobs to {output_path}")
    
    # Display some stats and preview
    print("\nDataFrame Shape:", df.shape)
    print("\nJobs with parsed Experience requirements:", df["Min_Years_Experience"].notnull().sum())
    print("Jobs with parsed Salary Range information:", df["Min_Salary"].notnull().sum())
    
    print("\nPreview of extracted experience requirements:")
    print(df[df["Min_Years_Experience"].notnull()][["Title", "Min_Years_Experience", "Max_Years_Experience", "Years_Experience_All"]].head())
    
    sal_jobs = df[df["Min_Salary"].notnull()]
    if not sal_jobs.empty:
        print("\nPreview of extracted salary info:")
        print(sal_jobs[["Title", "Location", "Min_Salary", "Max_Salary", "Salary_Type"]])