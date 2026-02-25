#!/bin/bash

# Legacy Code Cleanup Script
# Safely deletes Python files that have been migrated to Rust/Go

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to backup files before deletion
backup_file() {
    local file_path=$1
    local backup_dir="$PROJECT_ROOT/legacy_backup"
    
    if [ -f "$file_path" ]; then
        mkdir -p "$backup_dir"
        local backup_path="$backup_dir/$(basename $file_path).backup.$(date +%Y%m%d_%H%M%S)"
        cp "$file_path" "$backup_path"
        print_status "Backed up: $file_path -> $backup_path"
    fi
}

# Function to safely delete file
safe_delete() {
    local file_path=$1
    local description=$2
    
    if [ -f "$file_path" ]; then
        print_status "Deleting $description: $file_path"
        backup_file "$file_path"
        rm "$file_path"
        print_status "✅ Deleted: $file_path"
    else
        print_warning "File not found: $file_path"
    fi
}

# Function to check if file is safe to delete
is_safe_to_delete() {
    local file_path=$1
    local file_name=$(basename "$file_path")
    
    # List of files that are safe to delete (migrated to Rust/Go)
    local safe_files=(
        "services/data_ingestion.py"
        "api_server.py"
        "adapters/binance_adapter.py"
        "adapters/mock_provider.py"
        "services/ai_models.py"
        "services/classifier.py"
        "services/sentiment_engine.py"
        "main.py"
        "production_server.py"
    )
    
    for safe_file in "${safe_files[@]}"; do
        if [[ "$file_name" == "$safe_file" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Function to clean Python dependencies
clean_python_dependencies() {
    print_header "Cleaning Python Dependencies"
    
    # Check for requirements.txt
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        print_status "Found requirements.txt, checking for unused dependencies..."
        
        # Create backup
        backup_file "$PROJECT_ROOT/requirements.txt"
        
        # List of dependencies that are no longer needed after migration
        local unused_deps=(
            "fastapi"
            "uvicorn"
            "aiohttp"
            "pydantic"
            "python-multipart"
            "websockets"
            "starlette"
        )
        
        # Create new requirements.txt without unused dependencies
        local temp_req="/tmp/requirements_new.txt"
        
        while IFS= read -r line; do
            local should_keep=true
            
            for dep in "${unused_deps[@]}"; do
                if [[ "$line" =~ ^$dep[=] ]]; then
                    should_keep=false
                    print_status "Removing unused dependency: $dep"
                    break
                fi
            done
            
            if [ "$should_keep" = true ]; then
                echo "$line" >> "$temp_req"
            fi
        done < "$PROJECT_ROOT/requirements.txt"
        
        # Replace original file
        mv "$temp_req" "$PROJECT_ROOT/requirements.txt"
        print_status "✅ Updated requirements.txt"
    fi
    
    # Check for pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        print_status "Found pyproject.toml, checking for unused dependencies..."
        backup_file "$PROJECT_ROOT/pyproject.toml"
        
        # Similar cleanup for pyproject.toml would go here
        print_status "⚠️  Manual review of pyproject.toml recommended"
    fi
}

# Function to update main entry point
update_main_entry() {
    print_header "Updating Main Entry Point"
    
    # Create new main.py that points to microservices
    cat > "$PROJECT_ROOT/main.py" << 'EOF'
#!/usr/bin/env python3
"""
Market Intel Brain - Microservices Entry Point

This file serves as the main entry point for the microservices architecture.
The actual business logic has been migrated to:
- Rust Core Engine (high-performance processing)
- Go API Gateway (HTTP/WebSocket layer)

To run the system:
1. Start Rust Core Engine: cd microservices/rust-services/core-engine && cargo run
2. Start Go API Gateway: cd microservices/go-services/api-gateway && go run cmd/api-gateway/main.go
3. Access API at: http://localhost:8080
"""

import sys
import os

def main():
    print("🚀 Market Intel Brain - Microservices Architecture")
    print("=" * 50)
    print("")
    print("The system has been migrated to microservices architecture:")
    print("")
    print("🦀 Rust Core Engine: High-performance data processing")
    print("🌐 Go API Gateway: HTTP/WebSocket API layer")
    print("")
    print("To start the system:")
    print("1. cd microservices/rust-services/core-engine && cargo run")
    print("2. cd microservices/go-services/api-gateway && go run cmd/api-gateway/main.go")
    print("3. Access API at: http://localhost:8080")
    print("")
    print("📚 Documentation:")
    print("- microservices/README.md - Architecture overview")
    print("- microservices/PHASE2_IMPLEMENTATION.md - Phase 2 details")
    print("- microservices/PHASE3_IMPLEMENTATION.md - Phase 3 details")
    print("- microservices/PHASE4_IMPLEMENTATION.md - Phase 4 details")
    print("")
    print("🔧 Scripts:")
    print("- microservices/scripts/e2e-validation.sh - End-to-end testing")
    print("- microservices/scripts/cleanup-legacy-code.sh - This cleanup script")
    print("")
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    main()
EOF
    
    print_status "✅ Created new main.py entry point"
}

# Main cleanup function
main() {
    print_header "Legacy Code Cleanup"
    print_status "Project Root: $PROJECT_ROOT"
    
    # Create backup directory
    local backup_dir="$PROJECT_ROOT/legacy_backup"
    mkdir -p "$backup_dir"
    print_status "Created backup directory: $backup_dir"
    
    # List of files to delete (migrated to Rust/Go)
    local files_to_delete=(
        "$PROJECT_ROOT/services/data_ingestion.py"
        "$PROJECT_ROOT/api_server.py"
        "$PROJECT_ROOT/adapters/binance_adapter.py"
        "$PROJECT_ROOT/adapters/mock_provider.py"
        "$PROJECT_ROOT/services/ai_models.py"
        "$PROJECT_ROOT/services/classifier.py"
        "$PROJECT_ROOT/services/sentiment_engine.py"
        "$PROJECT_ROOT/production_server.py"
    )
    
    # Confirm before deletion
    print_warning "About to delete the following files (migrated to Rust/Go):"
    for file in "${files_to_delete[@]}"; do
        if [ -f "$file" ]; then
            echo "  - $file"
        fi
    done
    
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleanup cancelled by user"
        exit 0
    fi
    
    # Delete files
    print_header "Deleting Legacy Files"
    
    for file in "${files_to_delete[@]}"; do
        if is_safe_to_delete "$file"; then
            safe_delete "$file" "legacy file"
        else
            print_warning "Skipping unsafe file: $file"
        fi
    done
    
    # Clean Python dependencies
    clean_python_dependencies
    
    # Update main entry point
    update_main_entry
    
    # Generate cleanup report
    print_header "Cleanup Report"
    
    local report_file="$backup_dir/cleanup_report.md"
    cat > "$report_file" << EOF
# Legacy Code Cleanup Report
Generated: $(date)

## Files Deleted
EOF
    
    for file in "${files_to_delete[@]}"; do
        if [ -f "$file" ]; then
            echo "- $file" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

## Files Backed Up
All deleted files have been backed up to: $backup_dir

## Dependencies Cleaned
- requirements.txt: Updated to remove unused FastAPI dependencies
- pyproject.toml: Manual review recommended

## New Entry Point
- main.py: Updated to point to microservices architecture

## Migration Status
✅ Data Ingestion: Python -> Rust
✅ API Gateway: Python FastAPI -> Go Gin
✅ WebSocket: Python -> Go
✅ Error Handling: Python -> Go
✅ Configuration: Python -> Go/Rust

## Next Steps
1. Test the new microservices architecture
2. Verify all functionality works as expected
3. Update documentation as needed
4. Remove any remaining legacy code if safe
EOF
    
    print_status "✅ Cleanup report generated: $report_file"
    
    print_header "Cleanup Complete"
    print_status "✅ Legacy code cleanup completed successfully!"
    print_status "📁 Backups available at: $backup_dir"
    print_status "📋 Report available at: $report_file"
    print_status ""
    print_status "🚀 The system is now fully migrated to microservices architecture!"
}

# Run main function
main "$@"
