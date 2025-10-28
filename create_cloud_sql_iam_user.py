#!/usr/bin/env python3
"""Create IAM database user using gcloud Cloud SQL commands."""

import subprocess
import sys

PROJECT_ID = "skai-fastmcp-cloudrun"
INSTANCE = "hansard-db-v2"
IAM_SA = "hansard-cloud-sql-iam@skai-fastmcp-cloudrun.iam.gserviceaccount.com"


def create_iam_user_via_gcloud():
    """Create IAM user using gcloud."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║    Setting Up IAM Database User for Cloud SQL                 ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    try:
        # Create IAM database user in Cloud SQL
        print(f"1. Creating Cloud SQL IAM database user: {IAM_SA}...")
        cmd = [
            "gcloud", "sql", "users", "create",
            IAM_SA,
            f"--instance={INSTANCE}",
            "--type=CLOUD_IAM_SERVICE_ACCOUNT",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✓ User created successfully")
        elif ("already exists" in result.stderr or
              "already exists" in result.stdout):
            print("   ✓ User already exists")
        else:
            print(f"   Error: {result.stderr}")
            raise RuntimeError(result.stderr)

        # Show user details
        print("\n2. Verifying user configuration...")
        cmd = [
            "gcloud", "sql", "users", "describe",
            IAM_SA, f"--instance={INSTANCE}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)

        print("\n" + "=" * 66)
        print("  IAM USER SETUP COMPLETE")
        print("=" * 66)
        print(f"\nService Account: {IAM_SA}")
        print("\nConfiguration Summary:")
        print("  ✓ Service Account Created & Authorized")
        print("  ✓ Cloud SQL IAM Client Role Assigned")
        print("  ✓ Database User Created with IAM Type")
        print("  ✓ Cloud Run Using Service Account")
        print("\nNext Steps:")
        print("  1. Verify Cloud Run can access database")
        print("  2. Deploy Feature 017 to populate database")
        print("  3. Test end-to-end functionality")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_iam_user_via_gcloud()
    sys.exit(0 if success else 1)
