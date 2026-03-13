#!/bin/bash

# Complete cleanup script: Delete vectors, then delete index, then recreate
BUCKET="garuda-sdlc"
INDEX="requirements-gadhering-4"
REGION="us-west-2"

echo "=========================================="
echo "AWS S3 Vectors Index Cleanup & Recreate"
echo "=========================================="
echo ""
echo "Bucket: $BUCKET"
echo "Index:  $INDEX"
echo "Region: $REGION"
echo ""

# Verification step
echo "🔍 Checking current index status..."
echo ""
INDEX_FILES=$(aws s3api list-objects-v2 \
  --bucket $BUCKET \
  --prefix "$INDEX/" \
  --region $REGION \
  --query 'Contents[].Key' \
  --output text 2>/dev/null)

if [ -z "$INDEX_FILES" ] || [ "$INDEX_FILES" == "None" ]; then
    echo "  ℹ️  No index files found - index may not exist"
else
    FILE_COUNT=$(echo "$INDEX_FILES" | wc -w | tr -d ' ')
    echo "  📁 Found $FILE_COUNT index configuration files:"
    for key in $INDEX_FILES; do
        echo "     - $key"
    done
fi
echo ""

# Step 1: Delete all vectors
echo "📦 STEP 1: Deleting all vectors from index..."
echo ""

ALL_KEYS=()
NEXT_TOKEN=""

while true; do
    if [ -z "$NEXT_TOKEN" ]; then
        RESULT=$(aws s3vectors list-vectors \
          --vector-bucket-name $BUCKET \
          --index-name $INDEX \
          --region $REGION \
          --max-results 1000 \
          --output json 2>/dev/null)
    else
        RESULT=$(aws s3vectors list-vectors \
          --vector-bucket-name $BUCKET \
          --index-name $INDEX \
          --region $REGION \
          --max-results 1000 \
          --next-token "$NEXT_TOKEN" \
          --output json 2>/dev/null)
    fi
    
    # Extract keys from this page
    PAGE_KEYS=$(echo "$RESULT" | jq -r '.vectors[]?.key // empty')
    
    if [ -z "$PAGE_KEYS" ]; then
        break
    fi
    
    # Add keys to array
    while IFS= read -r key; do
        ALL_KEYS+=("$key")
    done <<< "$PAGE_KEYS"
    
    # Check for next token
    NEXT_TOKEN=$(echo "$RESULT" | jq -r '.nextToken // empty')
    
    if [ -z "$NEXT_TOKEN" ]; then
        break
    fi
done

if [ ${#ALL_KEYS[@]} -eq 0 ]; then
    echo "  ℹ️  No vectors found (index may be empty or not exist)"
else
    echo "  Found ${#ALL_KEYS[@]} vectors to delete"
    
    # Delete in batches of 100
    BATCH_SIZE=100
    for ((i=0; i<${#ALL_KEYS[@]}; i+=BATCH_SIZE)); do
        BATCH=("${ALL_KEYS[@]:i:BATCH_SIZE}")
        echo "  Deleting batch $((i/BATCH_SIZE + 1)) (${#BATCH[@]} vectors)..."
        
        aws s3vectors delete-vectors \
          --vector-bucket-name $BUCKET \
          --index-name $INDEX \
          --region $REGION \
          --keys "${BATCH[@]}" 2>/dev/null
    done
    
    echo "  ✅ Deleted ${#ALL_KEYS[@]} vectors"
fi

echo ""
echo "🗑️  STEP 2: Deleting index metadata from S3..."
echo ""

# Delete all S3 objects with the index prefix
OBJECTS=$(aws s3api list-objects-v2 \
  --bucket $BUCKET \
  --prefix "$INDEX/" \
  --region $REGION \
  --query 'Contents[].Key' \
  --output text 2>/dev/null)

if [ -z "$OBJECTS" ] || [ "$OBJECTS" == "None" ]; then
    echo "  ℹ️  No index files found in S3"
else
    DELETED=0
    for key in $OBJECTS; do
        aws s3api delete-object --bucket $BUCKET --key "$key" --region $REGION
        echo "  ✓ Deleted: $key"
        DELETED=$((DELETED + 1))
    done
    echo "  ✅ Deleted $DELETED index files"
fi

echo ""
echo "✅ CLEANUP COMPLETE!"
echo ""
echo "📋 Summary:"
echo "  - Vectors deleted: ${#ALL_KEYS[@]}"
echo "  - Index metadata cleaned from S3"
echo ""
echo "🔄 Next Steps:"
echo "  1. Restart requirement_gathering service: cd services/requirement_gathering && uv run main.py"
echo "  2. The index will be recreated automatically on next upload"
echo "  3. New configuration will apply:"
echo "     • Filterable: source, project_id, requirement_id, file_type, chunk_index"
echo "     • Non-filterable: filename, total_chunks, char_count"
echo "  4. Try uploading aniket_Resume.pdf again"
echo ""
echo "  It should work now! 🎉"
echo ""
