#!/bin/bash

# Startup script to ensure storage directory exists with sample data
# This script copies sample storage files to the storage directory if they don't exist

echo "Checking storage directory..."

STORAGE_DIR="./storage"
SAMPLE_STORAGE_DIR="./sample/storage"

# Check if storage directory exists
if [ ! -d "$STORAGE_DIR" ]; then
    echo "Storage directory does not exist. Creating and copying sample storage files..."
    mkdir -p "$STORAGE_DIR"

    # Copy all files from sample/storage to storage
    cp "$SAMPLE_STORAGE_DIR"/* "$STORAGE_DIR"/

    if [ $? -eq 0 ]; then
        echo "✅ Successfully copied sample storage files to storage directory"
        echo "Files copied:"
        ls -la "$STORAGE_DIR"
    else
        echo "❌ Error: Failed to copy sample storage files"
        exit 1
    fi
else
    echo "✅ Storage directory already exists"

    # Optional: Check if any files are missing and copy them
    echo "Checking for missing files..."
    MISSING_FILES=false

    for file in "$SAMPLE_STORAGE_DIR"/*; do
        filename=$(basename "$file")
        if [ ! -f "$STORAGE_DIR/$filename" ]; then
            echo "Missing file: $filename - copying..."
            cp "$file" "$STORAGE_DIR"/
            MISSING_FILES=true
        fi
    done

    if [ "$MISSING_FILES" = true ]; then
        echo "✅ Copied missing files"
    else
        echo "✅ All required files are present"
    fi
fi

echo "Startup check complete!"
