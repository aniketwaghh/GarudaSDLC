#!/bin/bash
#
# Create S3 Vector index with optimized metadata configuration
#
# This script creates the vector index with minimal filterable metadata
# to comply with AWS S3 Vectors' 2048 byte filterable metadata limit.
#
# Filterable fields (used in queries): source, project_id, meeting_id
# Non-filterable fields (display only): All other metadata
#
# IMPORTANT: These settings are PERMANENT and cannot be changed after creation.
# To change the configuration, you must delete and recreate the index.
#

set -e

BUCKET_NAME="garuda-sdlc"
INDEX_NAME="requirements-gadhering"
DATA_TYPE="float32"
DIMENSION=1536  # text-embedding-ada-002
DISTANCE_METRIC="cosine"

echo "=========================================="
echo "Creating S3 Vector Index"
echo "=========================================="
echo "Bucket:          ${BUCKET_NAME}"
echo "Index:           ${INDEX_NAME}"
echo "Data Type:       ${DATA_TYPE}"
echo "Dimension:       ${DIMENSION}"
echo "Distance Metric: ${DISTANCE_METRIC}"
echo ""
echo "Filterable metadata fields:"
echo "  - source (used for filtering meeting vs custom requirements)"
echo "  - project_id (used for project-level filtering)"
echo "  - meeting_id (used for meeting-specific filtering)"
echo ""
echo "Non-filterable metadata fields:"
echo "  - chunk_id (reference to database content)"
echo "  - start_time_formatted"
echo "  - end_time_formatted"
echo "  - bot_id"
echo "  - duration_ms"
echo "  - requirement_id"
echo "  - file_type"
echo "  - chunk_index"
echo "  - filename"
echo "  - total_chunks"
echo ""
echo "⚠️  IMPORTANT: Text content is NOT stored in metadata!"
echo "   (page_content_metadata_key=None prevents 2048 byte limit issues)"
echo ""
echo "⚠️  WARNING: Index configuration is PERMANENT after creation!"
echo "=========================================="
echo ""

# Create the index with non-filterable metadata keys
aws s3vectors create-index \
  --vector-bucket-name "${BUCKET_NAME}" \
  --index-name "${INDEX_NAME}" \
  --data-type "${DATA_TYPE}" \
  --dimension ${DIMENSION} \
  --distance-metric "${DISTANCE_METRIC}" \
  --metadata-configuration '{
    "nonFilterableMetadataKeys": [
      "chunk_id",
      "start_time_formatted",
      "end_time_formatted",
      "bot_id",
      "duration_ms",
      "requirement_id",
      "file_type",
      "chunk_index",
      "filename",
      "total_chunks"
    ]
  }'

echo ""
echo "✅ Index created successfully!"
echo ""
echo "Next steps:"
echo "1. Restart the requirement_gathering service"
echo "2. Upload test documents (including large PDFs)"
echo "3. Verify uploads succeed with minimal filterable metadata"
echo ""
