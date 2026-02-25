#!/bin/bash

# Redis Cache Flush Script for Market Intel Brain
# Safely clears specific Redis cache keys without downtime

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="market-intel-brain"
REDIS_SERVICE="redis"
REDIS_PORT="6379"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Redis cache patterns
declare -A CACHE_PATTERNS=(
    ["market-data"]="market:data:*"
    ["news-data"]="news:data:*"
    ["user-sessions"]="session:*"
    ["api-cache"]="api:cache:*"
    ["rate-limits"]="rate:limit:*"
    ["auth-tokens"]="auth:token:*"
    ["metrics-cache"]="metrics:*"
    ["config-cache"]="config:*"
)

# Print functions
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

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if redis-cli is available
    if ! command -v redis-cli &> /dev/null; then
        print_error "redis-cli is not installed. Please install redis-cli first."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Get Redis pod name
get_redis_pod() {
    local redis_pod=$(kubectl get pods -n $NAMESPACE -l app=$REDIS_SERVICE -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$redis_pod" ]]; then
        print_error "Redis pod not found in namespace $NAMESPACE"
        return 1
    fi
    
    echo "$redis_pod"
}

# Check Redis connectivity
check_redis_connectivity() {
    local redis_pod=$1
    
    print_status "Checking Redis connectivity..."
    
    # Test basic connectivity
    if ! kubectl exec $redis_pod -n $NAMESPACE -- redis-cli ping > /dev/null 2>&1; then
        print_error "Cannot connect to Redis"
        return 1
    fi
    
    # Get Redis info
    local redis_info=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli info server 2>/dev/null)
    local redis_version=$(echo "$redis_info" | grep "redis_version" | cut -d: -f2 | tr -d '\r')
    local redis_mode=$(echo "$redis_info" | grep "redis_mode" | cut -d: -f2 | tr -d '\r')
    
    print_status "Redis version: $redis_version, mode: $redis_mode"
    
    return 0
}

# Get Redis memory usage
get_redis_memory_usage() {
    local redis_pod=$1
    
    local memory_info=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli info memory 2>/dev/null)
    local used_memory=$(echo "$memory_info" | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
    local max_memory=$(echo "$memory_info" | grep "maxmemory_human" | cut -d: -f2 | tr -d '\r')
    
    print_status "Redis memory usage: $used_memory / $max_memory"
}

# Count keys matching pattern
count_keys() {
    local redis_pod=$1
    local pattern=$2
    
    local key_count=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli --eval - <<EOF
local pattern = ARGV[1]
local count = 0
local cursor = 0
repeat
    local result = redis.call('SCAN', cursor, 'MATCH', pattern)
    cursor = tonumber(result[1])
    local keys = result[2]
    count = count + #keys
until cursor == 0
return count
EOF "$pattern" 2>/dev/null)
    
    echo "$key_count"
}

# List keys matching pattern (limited)
list_keys() {
    local redis_pod=$1
    local pattern=$2
    local limit=${3:-10}
    
    local keys=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli --eval - <<EOF
local pattern = ARGV[1]
local limit = tonumber(ARGV[2])
local cursor = 0
local all_keys = {}
repeat
    local result = redis.call('SCAN', cursor, 'MATCH', pattern)
    cursor = tonumber(result[1])
    local keys = result[2]
    for i = 1, #keys do
        table.insert(all_keys, keys[i])
        if #all_keys >= limit then
            break
        end
    end
until cursor == 0 or #all_keys >= limit
return all_keys
EOF "$pattern" "$limit" 2>/dev/null)
    
    echo "$keys"
}

# Backup Redis data before flush
backup_redis_data() {
    local redis_pod=$1
    local pattern=$2
    local backup_dir="$PROJECT_ROOT/backups/redis/$(date +%Y%m%d_%H%M%S)"
    
    print_status "Backing up Redis data for pattern: $pattern"
    
    mkdir -p "$backup_dir"
    
    # Get all keys matching pattern
    local keys=$(list_keys "$redis_pod" "$pattern" 1000)
    
    if [[ -z "$keys" ]]; then
        print_status "No keys found matching pattern: $pattern"
        echo "$backup_dir"
        return 0
    fi
    
    # Backup each key
    local backup_file="$backup_dir/redis-backup-$(echo "$pattern" | tr '*:' '-').json"
    echo "[" > "$backup_file"
    
    local first=true
    for key in $keys; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$backup_file"
        fi
        
        local key_type=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli type "$key" 2>/dev/null)
        local ttl=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli ttl "$key" 2>/dev/null)
        
        case "$key_type" in
            "string")
                local value=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli --raw get "$key" 2>/dev/null)
                echo "{\"key\":\"$key\",\"type\":\"string\",\"ttl\":$ttl,\"value\":\"$value\"}" >> "$backup_file"
                ;;
            "hash")
                local hash_data=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli hgetall "$key" 2>/dev/null)
                echo "{\"key\":\"$key\",\"type\":\"hash\",\"ttl\":$ttl,\"data\":\"$hash_data\"}" >> "$backup_file"
                ;;
            "list")
                local list_data=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli lrange "$key" 0 -1 2>/dev/null)
                echo "{\"key\":\"$key\",\"type\":\"list\",\"ttl\":$ttl,\"data\":\"$list_data\"}" >> "$backup_file"
                ;;
            "set")
                local set_data=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli smembers "$key" 2>/dev/null)
                echo "{\"key\":\"$key\",\"type\":\"set\",\"ttl\":$ttl,\"data\":\"$set_data\"}" >> "$backup_file"
                ;;
            "zset")
                local zset_data=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli zrange "$key" 0 -1 withscores 2>/dev/null)
                echo "{\"key\":\"$key\",\"type\":\"zset\",\"ttl\":$ttl,\"data\":\"$zset_data\"}" >> "$backup_file"
                ;;
        esac
    done
    
    echo "]" >> "$backup_file"
    
    local key_count=$(count_keys "$redis_pod" "$pattern")
    print_status "Backed up $key_count keys to: $backup_file"
    
    echo "$backup_dir"
}

# Flush keys matching pattern
flush_keys() {
    local redis_pod=$1
    local pattern=$2
    local batch_size=${3:-100}
    
    print_status "Flushing keys matching pattern: $pattern"
    
    # Count keys before flush
    local key_count_before=$(count_keys "$redis_pod" "$pattern")
    print_status "Keys to flush: $key_count_before"
    
    if [[ $key_count_before -eq 0 ]]; then
        print_status "No keys found matching pattern: $pattern"
        return 0
    fi
    
    # Flush in batches to avoid blocking Redis
    local cursor=0
    local total_flushed=0
    
    while true; do
        # Get batch of keys
        local batch_keys=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli --eval - <<EOF
local pattern = ARGV[1]
local batch_size = tonumber(ARGV[2])
local cursor = tonumber(ARGV[3])
local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', batch_size)
cursor = tonumber(result[1])
local keys = result[2]
return cursor, keys
EOF "$pattern" "$batch_size" "$cursor" 2>/dev/null)
        
        if [[ -z "$batch_keys" ]]; then
            break
        fi
        
        # Extract cursor and keys
        local new_cursor=$(echo "$batch_keys" | head -1)
        local keys=$(echo "$batch_keys" | tail -n +2)
        
        # Flush the batch
        if [[ -n "$keys" ]]; then
            local delete_result=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli --eval - <<EOF
local keys = {}
for i = 1, #ARGV do
    table.insert(keys, ARGV[i])
end
return redis.call('DEL', unpack(keys))
EOF $keys 2>/dev/null)
            
            local deleted_count=$(echo "$delete_result" | tr -d '\r')
            total_flushed=$((total_flushed + deleted_count))
            
            print_status "Flushed $deleted_count keys (total: $total_flushed)"
        fi
        
        # Update cursor
        cursor=$new_cursor
        
        # Check if we're done
        if [[ "$cursor" == "0" ]]; then
            break
        fi
        
        # Small delay to avoid overwhelming Redis
        sleep 0.1
    done
    
    print_status "Flush completed. Total keys flushed: $total_flushed"
    
    # Verify flush
    local key_count_after=$(count_keys "$redis_pod" "$pattern")
    if [[ $key_count_after -eq 0 ]]; then
        print_status "✓ All keys flushed successfully"
    else
        print_warning "⚠ $key_count_after keys still remain"
    fi
    
    return 0
}

# Flush specific cache type
flush_cache_type() {
    local cache_type=$1
    local pattern=${CACHE_PATTERNS[$cache_type]}
    
    if [[ -z "$pattern" ]]; then
        print_error "Unknown cache type: $cache_type"
        print_status "Available cache types: ${!CACHE_PATTERNS[*]}"
        return 1
    fi
    
    print_header "Flushing Cache Type: $cache_type"
    
    local redis_pod=$(get_redis_pod)
    check_redis_connectivity "$redis_pod"
    
    # Show current state
    local key_count=$(count_keys "$redis_pod" "$pattern")
    print_status "Current keys matching $pattern: $key_count"
    
    if [[ $key_count -eq 0 ]]; then
        print_status "No keys to flush for $cache_type"
        return 0
    fi
    
    # Confirm flush
    if [[ "${FORCE_FLUSH:-false}" != "true" ]]; then
        echo -n "Are you sure you want to flush $key_count keys for $cache_type? (y/N): "
        read -r confirmation
        if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
            print_status "Flush cancelled"
            return 0
        fi
    fi
    
    # Backup before flush
    local backup_dir=$(backup_redis_data "$redis_pod" "$pattern")
    
    # Flush keys
    flush_keys "$redis_pod" "$pattern"
    
    # Generate flush report
    generate_flush_report "$cache_type" "$pattern" "$backup_dir"
    
    return 0
}

# Flush custom pattern
flush_custom_pattern() {
    local pattern=$1
    
    print_header "Flushing Custom Pattern: $pattern"
    
    local redis_pod=$(get_redis_pod)
    check_redis_connectivity "$redis_pod"
    
    # Show current state
    local key_count=$(count_keys "$redis_pod" "$pattern")
    print_status "Current keys matching $pattern: $key_count"
    
    if [[ $key_count -eq 0 ]]; then
        print_status "No keys to flush for pattern: $pattern"
        return 0
    fi
    
    # Confirm flush
    if [[ "${FORCE_FLUSH:-false}" != "true" ]]; then
        echo -n "Are you sure you want to flush $key_count keys matching '$pattern'? (y/N): "
        read -r confirmation
        if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
            print_status "Flush cancelled"
            return 0
        fi
    fi
    
    # Backup before flush
    local backup_dir=$(backup_redis_data "$redis_pod" "$pattern")
    
    # Flush keys
    flush_keys "$redis_pod" "$pattern"
    
    # Generate flush report
    generate_flush_report "custom" "$pattern" "$backup_dir"
    
    return 0
}

# Generate flush report
generate_flush_report() {
    local cache_type=$1
    local pattern=$2
    local backup_dir=$3
    local report_file="$backup_dir/flush-report.md"
    
    print_status "Generating flush report: $report_file"
    
    cat > "$report_file" << EOF
# Redis Cache Flush Report

## Cache Type: $cache_type
## Pattern: $pattern
## Flush Date: $(date)
## Namespace: $NAMESPACE

## Pre-Flush Status
- Keys matching pattern: $(count_keys $(get_redis_pod) "$pattern")
- Backup location: $backup_dir

## Flush Process
- Method: Batch deletion
- Status: Completed
- Duration: \$(date -d "\$(date)" +%s) seconds

## Post-Flush Verification
- Keys remaining: $(count_keys $(get_redis_pod) "$pattern")
- Status: \$(count_keys $(get_redis_pod) "$pattern" -eq 0 && echo "Complete" || echo "Partial")

## Files Backed Up
- Redis Data: redis-backup-$(echo "$pattern" | tr '*:' '-').json

## Recovery Instructions
If issues occur, restore from backup:
\`\`\`bash
# Navigate to backup directory
cd $backup_dir

# Restore data (example for string keys)
kubectl exec <redis-pod> -n $NAMESPACE -- redis-cli --eval - <<EOF
local data = require('json.decode')(io.open('$backup_dir/redis-backup-$(echo "$pattern" | tr '*:' '-').json'):read('*a'))
for i, item in ipairs(data) do
    if item.type == 'string' then
        redis.call('SET', item.key, item.value)
        if item.ttl > 0 then
            redis.call('EXPIRE', item.key, item.ttl)
        end
    end
end
EOF
\`\`\`

## Next Steps
1. Monitor application performance
2. Check cache hit rates
3. Verify application functionality
4. Monitor Redis memory usage
EOF
    
    print_status "Flush report generated: $report_file"
}

# Show Redis statistics
show_redis_stats() {
    print_header "Redis Statistics"
    
    local redis_pod=$(get_redis_pod)
    check_redis_connectivity "$redis_pod"
    
    # General info
    local redis_info=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli info server 2>/dev/null)
    echo "Redis Server Info:"
    echo "$redis_info" | grep -E "(redis_version|redis_mode|uptime_in_seconds|connected_clients|used_memory_human|maxmemory_human)"
    
    echo ""
    echo "Cache Statistics:"
    
    # Show key counts for each pattern
    for cache_type in "${!CACHE_PATTERNS[@]}"; do
        local pattern=${CACHE_PATTERNS[$cache_type]}
        local key_count=$(count_keys "$redis_pod" "$pattern")
        echo "  $cache_type: $key_count keys"
    done
    
    echo ""
    echo "Memory Usage:"
    get_redis_memory_usage "$redis_pod"
    
    echo ""
    echo "Slow Log:"
    local slow_log=$(kubectl exec $redis_pod -n $NAMESPACE -- redis-cli slowlog get 10 2>/dev/null)
    if [[ -n "$slow_log" ]]; then
        echo "$slow_log"
    else
        echo "  No slow queries logged"
    fi
}

# List available cache types
list_cache_types() {
    print_header "Available Cache Types"
    
    echo "Configured cache types:"
    for cache_type in "${!CACHE_PATTERNS[@]}"; do
        local pattern=${CACHE_PATTERNS[$cache_type]}
        local redis_pod=$(get_redis_pod)
        local key_count=0
        
        if check_redis_connectivity "$redis_pod" &> /dev/null; then
            key_count=$(count_keys "$redis_pod" "$pattern")
        fi
        
        echo "  $cache_type: $pattern ($key_count keys)"
    done
}

# Main execution
main() {
    case "${1:-help}" in
        "flush")
            if [[ -z "$2" ]]; then
                print_error "Cache type is required"
                echo "Usage: $0 flush <cache-type>"
                echo "Available cache types: ${!CACHE_PATTERNS[*]}"
                echo "Or use 'custom' to specify a pattern"
                exit 1
            fi
            
            if [[ "$2" == "custom" ]]; then
                if [[ -z "$3" ]]; then
                    print_error "Pattern is required for custom flush"
                    echo "Usage: $0 flush custom <pattern>"
                    exit 1
                fi
                flush_custom_pattern "$3"
            else
                flush_cache_type "$2"
            fi
            ;;
        "stats")
            show_redis_stats
            ;;
        "list")
            list_cache_types
            ;;
        "count")
            if [[ -z "$2" ]]; then
                print_error "Pattern is required"
                echo "Usage: $0 count <pattern>"
                exit 1
            fi
            local redis_pod=$(get_redis_pod)
            check_redis_connectivity "$redis_pod"
            count_keys "$redis_pod" "$2"
            ;;
        "backup")
            if [[ -z "$2" ]]; then
                print_error "Pattern is required"
                echo "Usage: $0 backup <pattern>"
                exit 1
            fi
            local redis_pod=$(get_redis_pod)
            check_redis_connectivity "$redis_pod"
            backup_redis_data "$redis_pod" "$2"
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Redis Cache Flush Script"
            echo ""
            echo "Usage: $0 {flush|stats|list|count|backup|help}"
            echo ""
            echo "Commands:"
            echo "  flush <type>           - Flush cache type (or 'custom <pattern>')"
            echo "  stats                  - Show Redis statistics"
            echo "  list                   - List available cache types"
            echo "  count <pattern>         - Count keys matching pattern"
            echo "  backup <pattern>        - Backup keys matching pattern"
            echo "  help                   - Show this help message"
            echo ""
            echo "Available cache types: ${!CACHE_PATTERNS[*]}"
            echo ""
            echo "Environment variables:"
            echo "  FORCE_FLUSH=true        - Skip confirmation prompts"
            echo ""
            echo "Examples:"
            echo "  $0 flush market-data"
            echo "  $0 flush custom 'user:*'"
            echo "  $0 stats"
            echo "  $0 list"
            echo "  $0 count 'api:cache:*'"
            echo "  $0 backup 'session:*'"
            echo "  FORCE_FLUSH=true $0 flush news-data"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
