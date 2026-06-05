import os
import pandas as pd
from fetch_all_jobs import upload_to_supabase

def main():
    csv_path = os.path.join(os.path.dirname(__file__), "data_center_jobs.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return
        
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Replace nan with None so it translates correctly to JSON nulls
    df = df.where(pd.notnull(df), None)
    
    records = df.to_dict(orient="records")
    upload_to_supabase(records)
    print("Done!")

if __name__ == "__main__":
    main()
