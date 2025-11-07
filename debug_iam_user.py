"""Debug script to identify IAM user in Cloud Run environment.

Run this in Cloud Run to see what IAM user is being detected.
"""
import os
import sys

print("=" * 80)
print("IAM USER DETECTION DEBUG")
print("=" * 80)

# Check environment
print("\n📋 Environment Variables:")
print(f"  USE_IAM_AUTH: {os.getenv('USE_IAM_AUTH')}")
print(f"  CLOUDSQL_USER: {os.getenv('CLOUDSQL_USER', 'NOT SET')}")
print(f"  K_SERVICE: {os.getenv('K_SERVICE', 'NOT SET')} (Cloud Run indicator)")
print(f"  GCP_PROJECT_ID: {os.getenv('GCP_PROJECT_ID', 'NOT SET')}")

# Try google.auth.default()
print("\n🔐 Attempting google.auth.default()...")
try:
    import google.auth
    credentials, project = google.auth.default()
    print(f"  ✅ Credentials type: {type(credentials).__name__}")
    print(f"  ✅ Project: {project}")
    
    # Check for service account email
    if hasattr(credentials, 'service_account_email'):
        print(f"  ✅ Service account email: {credentials.service_account_email}")
    elif hasattr(credentials, '_service_account_email'):
        print(f"  ✅ Service account email: {credentials._service_account_email}")
    else:
        print(f"  ⚠️  No service_account_email attribute found")
        print(f"  📋 Available attributes: {[a for a in dir(credentials) if not a.startswith('_')]}")
except Exception as e:
    print(f"  ❌ Failed: {e}")

# Try metadata server
print("\n🌐 Attempting metadata server query...")
if os.getenv('K_SERVICE'):  # Running in Cloud Run
    try:
        import requests
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(metadata_url, headers=headers, timeout=1)
        if response.status_code == 200:
            email = response.text.strip()
            print(f"  ✅ Service account email from metadata: {email}")
        else:
            print(f"  ❌ Metadata server returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
else:
    print("  ⏭️  Skipped (not in Cloud Run)")

# Try gcloud (local fallback)
print("\n🔧 Attempting gcloud config...")
try:
    import subprocess
    result = subprocess.check_output(
        ['gcloud', 'config', 'get-value', 'account'],
        text=True,
        stderr=subprocess.DEVNULL
    ).strip()
    if result and '@' in result:
        print(f"  ✅ gcloud account: {result}")
    else:
        print(f"  ⚠️  gcloud returned: {result}")
except Exception as e:
    print(f"  ❌ Failed: {e}")

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)

# Final determination logic (matches cloud_sql_engine.py)
iam_user = None

try:
    import google.auth
    credentials, project = google.auth.default()
    if hasattr(credentials, 'service_account_email'):
        iam_user = credentials.service_account_email
    elif hasattr(credentials, '_service_account_email'):
        iam_user = credentials._service_account_email
except Exception:
    pass

if not iam_user and os.getenv('K_SERVICE'):
    try:
        import requests
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(metadata_url, headers=headers, timeout=1)
        if response.status_code == 200:
            iam_user = response.text.strip()
    except Exception:
        pass

if not iam_user:
    try:
        import subprocess
        result = subprocess.check_output(
            ['gcloud', 'config', 'get-value', 'account'],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        if result and '@' in result:
            iam_user = result
    except Exception:
        pass

if not iam_user:
    iam_user = "postgres"
    print("⚠️  WARNING: No IAM user detected, falling back to 'postgres'")

print(f"\n🎯 FINAL IAM USER: {iam_user}")
print("=" * 80)
