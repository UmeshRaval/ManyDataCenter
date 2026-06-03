import os
import requests
import pandas as pd

# List of major data center operators and hyperscalers
OPERATORS_DATA = [
    {
        "id": "equinix",
        "name": "Equinix",
        "code": "EQIX",
        "website": "https://www.equinix.com",
        "headquarters": "Redwood City, California, USA",
        "operator_type": "Colocation",
        "description": "Global digital infrastructure company operating over 240 IBX data centers across 5 continents, specializing in retail colocation and interconnection."
    },
    {
        "id": "digital-realty",
        "name": "Digital Realty",
        "code": "DLR",
        "website": "https://www.digitalrealty.com",
        "headquarters": "Austin, Texas, USA",
        "operator_type": "Colocation & Wholesale",
        "description": "One of the largest global providers of data center, colocation, and interconnection solutions, operating over 300 facilities worldwide."
    },
    {
        "id": "cyrusone",
        "name": "CyrusOne",
        "code": "CONE",
        "website": "https://cyrusone.com",
        "headquarters": "Dallas, Texas, USA",
        "operator_type": "Wholesale & Colocation",
        "description": "Specializes in highly reliable, enterprise-class, carrier-neutral data centers, serving many Fortune 1000 customers."
    },
    {
        "id": "coresite",
        "name": "CoreSite",
        "code": "COR",
        "website": "https://www.coresite.com",
        "headquarters": "Denver, Colorado, USA",
        "operator_type": "Colocation",
        "description": "An American real estate investment trust that invests in carrier-neutral data centers, owned by American Tower."
    },
    {
        "id": "ntt-gdc",
        "name": "NTT Global Data Centers",
        "code": "NTT",
        "website": "https://datacenter.hello.global.ntt",
        "headquarters": "London, UK / Tokyo, Japan",
        "operator_type": "Colocation & Wholesale",
        "description": "Part of NTT Ltd., operating one of the largest data center platforms globally across Europe, North America, Asia, and Africa."
    },
    {
        "id": "qts",
        "name": "QTS Realty Trust",
        "code": "QTS",
        "website": "https://www.qtsdatacenters.com",
        "headquarters": "Overland Park, Kansas, USA",
        "operator_type": "Wholesale & Colocation",
        "description": "A leading provider of secure, compliant data center solutions, owned by Blackstone."
    },
    {
        "id": "vantage",
        "name": "Vantage Data Centers",
        "code": "VANT",
        "website": "https://vantage-dc.com",
        "headquarters": "Denver, Colorado, USA",
        "operator_type": "Wholesale",
        "description": "Powers hyperscalers, cloud providers, and large enterprises with highly customized, scalable, and sustainable campus facilities."
    },
    {
        "id": "edgeconnex",
        "name": "EdgeConneX",
        "code": "EDGX",
        "website": "https://www.edgeconnex.com",
        "headquarters": "Herndon, Virginia, USA",
        "operator_type": "Edge & Wholesale",
        "description": "Pioneered the 'Edge' data center model to deliver content and applications closer to users, operating over 50 markets globally."
    },
    {
        "id": "iron-mountain",
        "name": "Iron Mountain Data Centers",
        "code": "IRM",
        "website": "https://www.ironmountain.com/data-centers",
        "headquarters": "Boston, Massachusetts, USA",
        "operator_type": "Colocation",
        "description": "Operates highly secure, compliant, and energy-efficient colocation data centers with a strong focus on enterprise records management integration."
    },
    {
        "id": "flexential",
        "name": "Flexential",
        "code": "FLEX",
        "website": "https://www.flexential.com",
        "headquarters": "Charlotte, North Carolina, USA",
        "operator_type": "Colocation & Hybrid IT",
        "description": "Operates data centers across the US, offering colocation, cloud, connectivity, disaster recovery, and managed services."
    },
    {
        "id": "compass",
        "name": "Compass Datacenters",
        "code": "COMP",
        "website": "https://www.compassdatacenters.com",
        "headquarters": "Dallas, Texas, USA",
        "operator_type": "Wholesale",
        "description": "Builds highly customized, dedicated wholesale data centers for cloud providers, network operators, and large enterprises."
    },
    {
        "id": "sabey",
        "name": "Sabey Data Centers",
        "code": "SABY",
        "website": "https://sabeydatacenters.com",
        "headquarters": "Seattle, Washington, USA",
        "operator_type": "Wholesale & Colocation",
        "description": "One of the largest privately-owned multi-tenant data center developers and operators in the United States."
    },
    {
        "id": "aws",
        "name": "Amazon Web Services",
        "code": "AWS",
        "website": "https://aws.amazon.com",
        "headquarters": "Seattle, Washington, USA",
        "operator_type": "Hyperscaler",
        "description": "The world's most comprehensive and broadly adopted cloud platform, operating hundreds of proprietary data centers globally."
    },
    {
        "id": "azure",
        "name": "Microsoft Azure",
        "code": "MSFT",
        "website": "https://azure.microsoft.com",
        "headquarters": "Redmond, Washington, USA",
        "operator_type": "Hyperscaler",
        "description": "Global cloud computing platform with data centers spanning over 60 regions worldwide."
    },
    {
        "id": "gcp",
        "name": "Google Cloud Platform",
        "code": "GCP",
        "website": "https://cloud.google.com",
        "headquarters": "Mountain View, California, USA",
        "operator_type": "Hyperscaler",
        "description": "Global scale cloud computing platform powered by Google's highly advanced, energy-efficient data center network."
    }
]

def upload_operators():
    # Save a local CSV copy first
    df = pd.DataFrame(OPERATORS_DATA)
    output_path = os.path.join(os.path.dirname(__file__), "operators.csv")
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} operators locally to {output_path}")

    # Check for Supabase configuration
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Note: SUPABASE_URL or SUPABASE_KEY environment variables not set. Skipping Supabase upload.")
        return
        
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # Upsert based on primary key 'id'
    }
    
    url = f"{supabase_url.rstrip('/')}/rest/v1/data_center_operators"
    
    print(f"Uploading {len(OPERATORS_DATA)} operators to Supabase...")
    try:
        response = requests.post(url, json=OPERATORS_DATA, headers=headers)
        response.raise_for_status()
        print("Successfully uploaded all operators to Supabase.")
    except Exception as e:
        print(f"Error uploading operators to Supabase: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Response detail:", e.response.text)

if __name__ == "__main__":
    upload_operators()
