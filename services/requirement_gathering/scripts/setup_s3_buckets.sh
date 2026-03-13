#!/bin/bash

# S3 Bucket Setup Script for GarudaSDLC
# This script creates the necessary S3 buckets with proper security settings

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  GarudaSDLC S3 Bucket Setup"
echo "========================================"
echo ""

# Configuration
REGION="${AWS_REGION:-us-west-2}"
MEDIA_BUCKET="${AWS_S3_MEDIA_BUCKET_NAME:-garuda-sdlc-media}"
VECTOR_BUCKET="${AWS_S3_VECTOR_BUCKET_NAME:-garuda-sdlc-vectors}"

echo -e "${BLUE}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Media Bucket: $MEDIA_BUCKET"
echo "  Vector Bucket: $VECTOR_BUCKET"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}⚠ AWS CLI not found. Please install it first:${NC}"
    echo "  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
echo -e "${BLUE}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${YELLOW}⚠ AWS credentials not configured. Please run:${NC}"
    echo "  aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS credentials verified${NC}"
echo ""

# Function to create bucket
create_bucket() {
    local bucket_name=$1
    local purpose=$2
    
    echo -e "${BLUE}Creating $purpose bucket: $bucket_name${NC}"
    
    # Check if bucket already exists
    if aws s3 ls "s3://$bucket_name" 2>&1 | grep -q "NoSuchBucket"; then
        # Create bucket
        if [ "$REGION" = "us-east-1" ]; then
            aws s3 mb "s3://$bucket_name"
        else
            aws s3 mb "s3://$bucket_name" --region "$REGION"
        fi
        echo -e "${GREEN}✓ Bucket created: $bucket_name${NC}"
    else
        echo -e "${YELLOW}⚠ Bucket already exists: $bucket_name${NC}"
    fi
    
    # Block all public access
    echo "  → Blocking public access..."
    aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    echo -e "${GREEN}✓ Public access blocked${NC}"
    
    # Enable versioning (recommended for media bucket)
    if [ "$purpose" = "media" ]; then
        echo "  → Enabling versioning..."
        aws s3api put-bucket-versioning \
            --bucket "$bucket_name" \
            --versioning-configuration Status=Enabled
        echo -e "${GREEN}✓ Versioning enabled${NC}"
    fi
    
    echo ""
}

# Create media bucket
create_bucket "$MEDIA_BUCKET" "media"

# Create vector bucket
create_bucket "$VECTOR_BUCKET" "vector"

# Summary
echo "========================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Created buckets:"
echo "  📦 $MEDIA_BUCKET (for videos, audio, transcripts)"
echo "  📦 $VECTOR_BUCKET (for vector embeddings)"
echo ""
echo "Next steps:"
echo "  1. Update your .env file with these bucket names"
echo "  2. Ensure IAM permissions are set correctly"
echo "  3. Restart your services"
echo ""
echo "To verify:"
echo "  aws s3 ls s3://$MEDIA_BUCKET"
echo "  aws s3 ls s3://$VECTOR_BUCKET"
echo ""
