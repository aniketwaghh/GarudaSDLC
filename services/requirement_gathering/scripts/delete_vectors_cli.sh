#!/bin/bash
BUCKET="garuda-sdlc"
INDEX="requirements-gadhering-4"
REGION="us-west-2"

echo "Fetching all keys from index $INDEX..."

# Fetch all keys - need to handle pagination with nextToken
ALL_KEYS=()
NEXT_TOKEN=""

while true; do
    if [ -z "$NEXT_TOKEN" ]; then
        RESULT=$(aws s3vectors list-vectors \
          --vector-bucket-name $BUCKET \
          --index-name $INDEX \
          --region $REGION \
          --max-results 1000 \
          --output json)
    else
        RESULT=$(aws s3vectors list-vectors \
          --vector-bucket-name $BUCKET \
          --index-name $INDEX \
          --region $REGION \
          --max-results 1000 \
          --next-token "$NEXT_TOKEN" \
          --output json)
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

# Check if index is already empty
if [ ${#ALL_KEYS[@]} -eq 0 ]; then
    echo "Index is already clean."
    exit 0
fi

echo "Found ${#ALL_KEYS[@]} vectors to delete."
echo "Deleting vectors..."

# Delete in batches of 100 (AWS may have limits)
BATCH_SIZE=100
for ((i=0; i<${#ALL_KEYS[@]}; i+=BATCH_SIZE)); do
    BATCH=("${ALL_KEYS[@]:i:BATCH_SIZE}")
    echo "  Deleting batch $((i/BATCH_SIZE + 1)) (${#BATCH[@]} vectors)..."
    
    aws s3vectors delete-vectors \
      --vector-bucket-name $BUCKET \
      --index-name $INDEX \
      --region $REGION \
      --keys "${BATCH[@]}"
done

echo "✅ Index cleaned successfully! Deleted ${#ALL_KEYS[@]} vectors."
