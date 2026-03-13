#!/bin/bash
# Configure CORS on S3 media bucket for video streaming

set -e

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BUCKET_NAME="${AWS_S3_MEDIA_BUCKET_NAME:-garuda-sdlc-media}"

echo "=================================================="
echo "  Configuring CORS for S3 Bucket: $BUCKET_NAME"
echo "=================================================="
echo ""

# Create CORS configuration
cat > /tmp/cors-config.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": [
        "*"
      ],
      "AllowedMethods": [
        "GET",
        "HEAD"
      ],
      "AllowedHeaders": [
        "*"
      ],
      "ExposeHeaders": [
        "ETag",
        "Content-Length",
        "Content-Type"
      ],
      "MaxAgeSeconds": 3600
    }
  ]
}
EOF

echo "📝 CORS Configuration:"
cat /tmp/cors-config.json
echo ""

# Apply CORS configuration
echo "🔧 Applying CORS configuration to bucket..."
aws s3api put-bucket-cors \
  --bucket "$BUCKET_NAME" \
  --cors-configuration file:///tmp/cors-config.json

if [ $? -eq 0 ]; then
    echo "✅ CORS configuration applied successfully!"
    echo ""
    echo "You can now stream videos from:"
    echo "  - http://localhost:5173 (Vite dev server)"
    echo "  - http://localhost:3000"
    echo "  - http://localhost:5174"
    echo "  - Vercel/Netlify deployments"
else
    echo "❌ Failed to apply CORS configuration"
    exit 1
fi

# Verify CORS configuration
echo ""
echo "📋 Verifying CORS configuration..."
aws s3api get-bucket-cors --bucket "$BUCKET_NAME"

# Cleanup
rm /tmp/cors-config.json

echo ""
echo "✅ Done! Try refreshing your frontend now."
