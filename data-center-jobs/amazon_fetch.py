import requests
import pandas as pd

def fetch_amazon_dc_jobs():
    # The internal JSON endpoint used by Amazon Jobs
    url = "https://www.amazon.jobs/en/search.json"
    
    params = {
        "base_query": "Data Center",
        "result_limit": 100, # Adjust with an offset loop for pagination
        "sort": "recent"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    
    jobs_list = []
    for job in data.get('jobs', []):
        jobs_list.append({
            "Job_ID": job.get("id_icims"),
            "Title": job.get("title"),
            "Location": job.get("location"),
            "Basic_Qualifications": job.get("basic_qualifications"),
            # Pay is often embedded in the description based on state transparency laws
            "Description": job.get("description") 
        })
        
    return pd.DataFrame(jobs_list)

df = fetch_amazon_dc_jobs()
print(df.head())