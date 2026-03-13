#!/bin/bash

# Script to inspect the current state of AWS S3 Vectors index
BUCKET="garuda-sdlc"
INDEX="requirements-gadhering-4"
REGION="us-west-2"

echo "=========================================="
echo "AWS S3 Vectors Index Inspection"
echo "=========================================="
echo ""
echo "Bucket: $BUCKET"
echo "Index:  $INDEX"
echo "Region: $REGION"
echo ""

# Check index configuration files
echo "📁 Index Configuration Files:"
echo ""
INDEX_FILES=$(aws s3api list-objects-v2 \
  --bucket $BUCKET \
  --prefix "$INDEX/" \
  --region $REGION \
  --query 'Contents[].[Key,Size,LastModified]' \
  --output text 2>/dev/null)

if [ -z "$INDEX_FILES" ] || [ "$INDEX_FILES" == "None" ]; then
    echo "  ⚠️  No index configuration found"
    echo "  This could mean:"
    echo "    - Index hasn't been created yet"
    echo "    - Index was deleted"
    echo "    - Wrong bucket/region"
else
    echo "$INDEX_FILES" | while IFS=$'\t' read -r key size modified; do
        SIZE_KB=$(echo "scale=2; $size/1024" | bc)
        echo "  📄 $key"
        echo "     Size: ${SIZE_KB} KB"
        echo "     Modified: $modified"
        echo ""
    done
fi

# Check vectors
echo "🔢 Vectors in Index:"
echo ""

RESULT=$(aws s3vectors list-vectors \
  --vector-bucket-name $BUCKET \
  --index-name $INDEX \
  --region $REGION \
  --max-results 10 \
  --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "  ⚠️  Could not list vectors (index may not exist)"
else
    TOTAL=$(echo "$RESULT" | jq -r '.vectors | length')
    
    if [ "$TOTAL" -eq 0 ]; then
        echo "  ℹ️  Index is empty (no vectors)"
    else
        echo "  📊 Showing first 10 of potentially many vectors:"
        echo ""
        echo "$RESULT" | jq -r '.vectors[] | "  ✓ \(.key)"'
        echo ""
        echo "  Total shown: $TOTAL"
    fi
fi

echo ""
echo "=========================================="
echo ""
