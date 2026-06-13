import os
import requests

def upload_h1b_wages(records):
    """
    Uploads a list of localized prevailing wage records to the Supabase h1b_prevailing_wages table.
    
    Expected record dictionary format:
    {
        "soc_code": "15-1244",
        "soc_title": "Network and Computer Systems Architects",
        "state_alpha": "TX",
        "msa_code": "26420",
        "msa_name": "Houston-The Woodlands-Sugar Land, TX",
        "prevailing_wage_level_1": 75000.00,
        "prevailing_wage_level_2": 95000.00,
        "prevailing_wage_level_3": 115000.00,
        "prevailing_wage_level_4": 140000.00,
        "wage_source": "OES"
    }
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("\nNote: SUPABASE_URL or SUPABASE_KEY environment variables not set. Skipping Supabase upload.")
        return
        
    chunk_size = 100
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
        # If you add a UNIQUE constraint to (soc_code, state_alpha, msa_code) in Supabase, 
        # you can uncomment the line below to perform an upsert instead of a standard insert:
        # "Prefer": "resolution=merge-duplicates"
    }
    
    url = f"{supabase_url.rstrip('/')}/rest/v1/h1b_prevailing_wages"
    
    print(f"\nUploading {len(records)} wage benchmarks to Supabase...")
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i+chunk_size]
        try:
            response = requests.post(url, json=chunk, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"Successfully uploaded chunk {i//chunk_size + 1} ({len(chunk)} records)...")
        except Exception as e:
            print(f"Error uploading chunk {i//chunk_size + 1} to Supabase: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("Response detail:", e.response.text)

def main():
    # TODO: Add logic here to:
    # 1. Read your target SOC Codes and Locations from your job listings
    # 2. Query the Department of Labor API or load the relevant slices of the H-1B CSV
    # 3. Transform the data into a list of dictionaries matching the target schema
    
    # Example dummy data for testing
    dummy_records = [
        {
            "soc_code": "15-1244",
            "soc_title": "Network and Computer Systems Architects",
            "state_alpha": "TX",
            "msa_code": "26420",
            "msa_name": "Houston-The Woodlands-Sugar Land, TX",
            "prevailing_wage_level_1": 78624.00,
            "prevailing_wage_level_2": 99757.00,
            "prevailing_wage_level_3": 120890.00,
            "prevailing_wage_level_4": 142022.00,
            "wage_source": "OES"
        }
    ]
    
    print("Preparing to upload H-1B prevailing wages data...")
    upload_h1b_wages(dummy_records)

if __name__ == "__main__":
    main()
