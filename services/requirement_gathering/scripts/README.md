# Utility Scripts

This directory contains maintenance and setup scripts for the GarudaSDLC requirement gathering service.

## 📁 Scripts Overview

### Setup Scripts

#### `setup_s3_buckets.sh`
**Purpose**: Initialize AWS S3 buckets for the application

**What it does**:
- Creates S3 media bucket (`garuda-sdlc-media`) for videos/audio/transcripts
- Creates S3 vector bucket (`garuda-sdlc-vectors`) for embeddings
- Configures private access (blocks all public access)
- Enables versioning on media bucket

**Usage**:
```bash
cd scripts
./setup_s3_buckets.sh
```

**When to use**: First-time setup or when buckets need to be recreated

---

#### `migrate_s3_columns.py`
**Purpose**: Database migration for S3 storage columns

**What it does**:
- Adds S3 key columns to `meet_history` table
  - `mp4_s3_key` - Video file location in S3
  - `audio_s3_key` - Audio file location in S3
  - `transcript_s3_key` - Transcript file location in S3
- Keeps legacy local path columns for backward compatibility

**Usage**:
```bash
cd scripts
uv run migrate_s3_columns.py
```

**When to use**: One-time migration when switching from local storage to S3

---

### Cleanup Scripts

#### `cleanup_dev_data.py`
**Purpose**: Complete development environment cleanup

**What it does**:
- Deletes all local downloads (meetings, recordings, transcripts)
- Clears `meet_history` database table
- Clears `meeting_schedules` database table
- Empties S3 media bucket (`garuda-sdlc-media`)
- Empties S3 vector bucket (`garuda-sdlc`)

**Usage**:
```bash
cd scripts
uv run cleanup_dev_data.py
```

**⚠️ Warning**: This is destructive! Only use in development.

**When to use**: 
- Cleaning dev environment between testing
- Removing test data before production deployment
- Resetting to fresh state

---

#### `delete_vectors_cli.sh`
**Purpose**: Delete all vector embeddings from AWS S3 Vectors index

**What it does**:
- Lists all vector keys from the S3 Vectors index
- Deletes vectors in batches (handles pagination)
- Preserves index structure for reuse
- Uses official AWS S3 Vectors CLI commands

**Usage**:
```bash
cd scripts
./delete_vectors_cli.sh
```

**When to use**:
- Clear vector embeddings without deleting bucket
- Reset RAG context for chatbot
- Remove outdated or test embeddings

---

## 🔧 Configuration

All scripts read from the `.env` file in the parent directory:

```bash
# AWS S3 Configuration
AWS_S3_VECTOR_BUCKET_NAME=garuda-sdlc
AWS_S3_MEDIA_BUCKET_NAME=garuda-sdlc-media
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Database
DATABASE_URL=sqlite:////path/to/garuda.db
```

## 📋 Common Workflows

### Fresh Development Setup
```bash
# 1. Create S3 buckets
./setup_s3_buckets.sh

# 2. Run database migration
uv run migrate_s3_columns.py

# 3. Start services
cd ..
uv run main.py
```

### Clean Development Environment
```bash
# Complete cleanup (recommended)
uv run cleanup_dev_data.py

# Or just vectors
./delete_vectors_cli.sh
```

### Production Deployment
```bash
# 1. Ensure S3 buckets exist
./setup_s3_buckets.sh

# 2. Run migration on production DB
DATABASE_URL=postgresql://... uv run migrate_s3_columns.py
```

## 🚨 Safety Notes

- ⚠️ `cleanup_dev_data.py` is **destructive** - use only in development
- ✅ All scripts validate AWS credentials before executing
- ✅ Scripts provide confirmation prompts for destructive operations
- ✅ Backups are not created - ensure you have your own backup strategy

## 📚 Related Documentation

- [S3_STORAGE.md](../S3_STORAGE.md) - Detailed S3 architecture and configuration
- [README.md](../README.md) - Main service documentation
