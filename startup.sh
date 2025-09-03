#!/bin/bash

# Startup script to ensure config, docs, and storage directories exist with sample data
# This script copies sample files to their respective directories if they don't exist

echo "Checking directories and config files..."

STORAGE_DIR="./storage"
SAMPLE_STORAGE_DIR="./sample/storage"

DOCS_DIR="./docs"
SAMPLE_DOCS_DIR="./sample/docs"

CONFIG_FILE="./config.json"
SAMPLE_CONFIG_FILE="./sample/config/config.json"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "$SAMPLE_CONFIG_FILE" ]; then
        echo "Config file does not exist. Copying sample config..."
        cp "$SAMPLE_CONFIG_FILE" "$CONFIG_FILE"

        if [ $? -eq 0 ]; then
            echo "✅ Successfully copied sample config.json"
            echo "You can edit config.json to customize your chatbot settings"
        else
            echo "❌ Error: Failed to copy sample config file"
            exit 1
        fi
    else
        echo "⚠️  Warning: Sample config file not found at $SAMPLE_CONFIG_FILE"
    fi
else
    echo "✅ Config file already exists"
fi

# Check if docs directory exists
if [ ! -d "$DOCS_DIR" ]; then
    if [ -d "$SAMPLE_DOCS_DIR" ]; then
        echo "Docs directory does not exist. Copying sample docs..."
        cp -r "$SAMPLE_DOCS_DIR" "$DOCS_DIR"

        if [ $? -eq 0 ]; then
            echo "✅ Successfully copied sample docs directory"
            echo "Files copied:"
            ls -la "$DOCS_DIR"
        else
            echo "❌ Error: Failed to copy sample docs directory"
            exit 1
        fi
    else
        echo "⚠️  Warning: Sample docs directory not found at $SAMPLE_DOCS_DIR"
        mkdir -p "$DOCS_DIR"
        echo "Created empty docs directory. Add your documents here."
    fi
else
    echo "✅ Docs directory already exists"
fi

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
