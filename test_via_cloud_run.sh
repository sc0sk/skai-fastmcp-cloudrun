#!/bin/bash
# Test search via Cloud Run Job (bypasses OAuth for testing)

echo "Testing search functionality via Cloud Run Job..."
echo "================================================"

# Create a temporary test script
cat > /tmp/test_search_job.py << 'PYTHON_EOF'
import asyncio
from src.tools.search import search_speeches

async def test():
    print("\n🔍 Testing: 'cost of living and inflation'")
    print("-" * 60)

    results = await search_speeches(
        query="cost of living and inflation",
        limit=5
    )

    print(f"\n✅ Found {len(results)} results!\n")

    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Speaker: {result.get('speaker', 'N/A')}")
        print(f"  Date: {result.get('date', 'N/A')}")
        print(f"  Party: {result.get('party', 'N/A')}")
        print(f"  Score: {result.get('relevance_score', 0):.3f}")
        print(f"  Excerpt: {result.get('excerpt', '')[:150]}...")
        print()

asyncio.run(test())
PYTHON_EOF

# Run the test
gcloud run jobs execute populate-hansard \
  --region=us-central1 \
  --args="python3,/tmp/test_search_job.py" \
  --wait
