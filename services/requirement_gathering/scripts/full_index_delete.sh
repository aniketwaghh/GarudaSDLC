#!/bin/bash

# Simple script to completely remove the S3 Vectors index
BUCKET="garuda-sdlc"
INDEX="requirements-gadhering-4"
REGION="us-west-2"

echo "=========================================="
echo "Delete S3 Vectors Index Completely"
echo "=========================================="
echo ""
echo "This will:"
echo "1. Delete all vectors using aws s3vectors"
echo "2. Delete all index metadata from S3"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🗑️  Step 1: Deleting all vectors..."
./scripts/delete_vectors_cli.sh

echo ""
echo "🗑️  Step 2: Deleting index metadata from S3..."
aws s3 rm s3://$BUCKET/$INDEX/ --recursive --region $REGION

echo ""
echo "✅ Complete! Index fully deleted."
echo ""
echo "Next: Restart requirement_gathering service and upload will recreate index with new config."
