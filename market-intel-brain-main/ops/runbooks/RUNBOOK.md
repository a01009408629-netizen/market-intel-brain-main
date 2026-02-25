# Market Intel Brain Operations Runbook

## Overview

This runbook provides step-by-step procedures for handling common incidents and operations in the Market Intel Brain system. Each procedure is linked to specific alerts from Phase 14 SLO monitoring and includes automated scripts for safe execution.

## Table of Contents

- [Certificate Rotation](#certificate-rotation)
- [Redis Cache Management](#redis-cache-management)
- [Debug Pod Operations](#debug-pod-operations)
- [Emergency Procedures](#emergency-procedures)
- [Alert Response Procedures](#alert-response-procedures)

---

## Certificate Rotation

### 🚨 Alert: APIGatewayHighErrorRate / CoreEngineHighErrorRate
**Trigger**: Certificate expiration or TLS handshake failures

### Automated Procedure

#### Using Shell Script
```bash
# List available certificates
./ops/runbooks/rotate-certs.sh list

# Rotate specific certificate
./ops/runbooks/rotate-certs.sh rotate api-gateway

# Force rotation (skip confirmation)
FORCE_FLUSH=true ./ops/runbooks/rotate-certs.sh rotate core-engine

# Check certificate expiration
./ops/runbooks/rotate-certs.sh check

# Validate certificate
./ops/runbooks/rotate-certs.sh validate api-gateway
```

#### Using Go CLI
```bash
# List certificates
./ops/cli/ops-cli cert list

# Rotate certificate with specific method
./ops/cli/ops-cli cert rotate api-gateway --method cert-manager

# Force rotation
./ops/cli/ops-cli cert rotate core-engine --force

# Validate certificate
./ops/cli/ops-cli cert validate api-gateway
```

### Manual Procedure

1. **Assess the Situation**
   ```bash
   # Check certificate expiration
   kubectl get secret api-gateway-tls -n market-intel-brain -o yaml
   
   # Check cert-manager status
   kubectl get certificate api-gateway-tls -n market-intel-brain
   ```

2. **Backup Current Certificate**
   ```bash
   # Backup to timestamped directory
   ./ops/runbooks/rotate-certs.sh backup api-gateway
   ```

3. **Rotate Certificate**
   ```bash
   # Using cert-manager (recommended)
   ./ops/runbooks/rotate-certs.sh rotate api-gateway cert-manager
   
   # Using Vault
   ./ops/runbooks/rotate-certs.sh rotate api-gateway vault
   ```

4. **Verify Rotation**
   ```bash
   # Validate new certificate
   ./ops/runbooks/rotate-certs.sh validate api-gateway
   
   # Test connectivity
   curl -k https://api.market-intel.com/api/v1/health
   ```

5. **Monitor Recovery**
   ```bash
   # Check pod restart status
   kubectl rollout status deployment/api-gateway -n market-intel-brain
   
   # Monitor SLO compliance
   curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:api_gateway:availability:rate5m"
   ```

### Available Certificates

| Certificate | Secret Name | Method | Backup |
|-------------|-------------|---------|--------|
| api-gateway | api-gateway-tls | cert-manager | ✅ |
| core-engine | core-engine-tls | cert-manager | ✅ |
| market-intel-ca | market-intel-ca | Vault | ✅ |
| api-gateway-mtls | api-gateway-mtls | cert-manager | ✅ |

### Troubleshooting

#### Certificate Rotation Fails
```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate status
kubectl describe certificate api-gateway-tls -n market-intel-brain

# Restore from backup
kubectl apply -f ./backups/certs/<timestamp>/api-gateway-secret.yaml
```

#### TLS Handshake Errors
```bash
# Check certificate details
openssl s_client -connect api.market-intel.com:443 -showcerts

# Debug with debug pod
./ops/runbooks/debug-pod.sh create api-gateway-<pod-id>
./ops/runbooks/debug-pod.sh interactive api-gateway-<pod-id>
```

---

## Redis Cache Management

### 🚨 Alert: APIGatewayHighLatency / CoreEngineHighLatency
**Trigger**: Cache performance degradation or memory saturation

### Automated Procedure

#### Using Shell Script
```bash
# List available cache types
./ops/runbooks/flush-redis.sh list

# Flush specific cache type
./ops/runbooks/flush-redis.sh flush market-data

# Flush custom pattern
./ops/runbooks/flush-redis.sh flush custom "user:*"

# Force flush (skip confirmation)
FORCE_FLUSH=true ./ops/runbooks/flush-redis.sh flush news-data

# Show Redis statistics
./ops/runbooks/flush-redis.sh stats

# Backup before flush
./ops/runbooks/flush-redis.sh backup "session:*"
```

#### Using Go CLI
```bash
# List cache types
./ops/cli/ops-cli redis list

# Flush cache with custom batch size
./ops/cli/ops-cli redis flush market-data --batch-size 200

# Force flush
./ops/cli/ops-cli redis flush news-data --force

# Show statistics
./ops/cli/ops-cli redis stats

# Backup specific pattern
./ops/cli/ops-cli redis backup "api:cache:*"
```

### Manual Procedure

1. **Assess Cache State**
   ```bash
   # Check Redis memory usage
   kubectl exec -it redis-<pod-id> -n market-intel-brain -- redis-cli info memory
   
   # Check key counts
   ./ops/runbooks/flush-redis.sh count "market:data:*"
   ```

2. **Backup Critical Data**
   ```bash
   # Backup user sessions before flush
   ./ops/runbooks/flush-redis.sh backup "session:*"
   
   # Backup API cache
   ./ops/runbooks/flush-redis.sh backup "api:cache:*"
   ```

3. **Flush Cache Safely**
   ```bash
   # Flush in batches to avoid blocking
   ./ops/runbooks/flush-redis.sh flush market-data
   
   # Monitor flush progress
   watch -n 5 './ops/runbooks/flush-redis.sh count "market:data:*"'
   ```

4. **Verify Recovery**
   ```bash
   # Check Redis memory after flush
   kubectl exec -it redis-<pod-id> -n market-intel-brain -- redis-cli info memory
   
   # Monitor application performance
   curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:api_gateway:latency_p99:rate5m"
   ```

### Available Cache Types

| Cache Type | Pattern | Backup | Description |
|-------------|---------|--------|-------------|
| market-data | `market:data:*` | ✅ | Market data cache |
| news-data | `news:data:*` | ✅ | News data cache |
| user-sessions | `session:*` | ✅ | User session cache |
| api-cache | `api:cache:*` | ✅ | API response cache |
| rate-limits | `rate:limit:*` | ✅ | Rate limiting cache |
| auth-tokens | `auth:token:*` | ✅ | Authentication tokens |
| metrics-cache | `metrics:*` | ✅ | Metrics cache |
| config-cache | `config:*` | ✅ | Configuration cache |

### Troubleshooting

#### Redis Flush Fails
```bash
# Check Redis connectivity
kubectl exec -it redis-<pod-id> -n market-intel-brain -- redis-cli ping

# Check Redis logs
kubectl logs redis-<pod-id> -n market-intel-brain

# Restore from backup
# Navigate to backup directory and restore JSON data
```

#### Performance Degradation After Flush
```bash
# Monitor cache hit rates
kubectl exec -it redis-<pod-id> -n market-intel-brain -- redis-cli info stats | grep keyspace

# Warm up cache
curl -X POST https://api.market-intel.com/api/v1/cache/warm-up

# Monitor latency recovery
curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:api_gateway:latency_p99:rate5m"
```

---

## Debug Pod Operations

### 🚨 Alert: SystemSLOBreached / CoreEngineHighLatency
**Trigger**: System-wide issues requiring deep debugging

### Automated Procedure

#### Using Shell Script
```bash
# List available pods
./ops/runbooks/debug-pod.sh list

# Create debug pod attached to target
./ops/runbooks/debug-pod.sh create api-gateway-<pod-id>

# Start interactive debug session
./ops/runbooks/debug-pod.sh interactive api-gateway-<pod-id>

# Execute network diagnostics
./ops/runbooks/debug-pod.sh exec api-gateway-<pod-id> network

# Execute system diagnostics
./ops/runbooks/debug-pod.sh exec api-gateway-<pod-id> system

# Generate debug report
./ops/runbooks/debug-pod.sh report api-gateway-<pod-id>

# Clean up debug pods
./ops/runbooks/debug-pod.sh cleanup
```

#### Using Go CLI
```bash
# Create debug pod with custom image
./ops/cli/ops-cli debug create api-gateway-<pod-id> --image nicolaka/netshoot

# Create debug pod with custom TTL
./ops/cli/ops-cli debug create core-engine-<pod-id> --ttl 7200

# Start interactive session
./ops/cli/ops-cli debug interactive api-gateway-<pod-id>

# Execute debug commands
./ops/cli/ops-cli debug exec api-gateway-<pod-id> network
./ops/cli/ops-cli debug exec api-gateway-<pod-id> system

# Clean up all debug pods
./ops/cli/ops-cli debug cleanup
```

### Manual Procedure

1. **Identify Target Pod**
   ```bash
   # List pods with issues
   kubectl get pods -n market-intel-brain --field-selector=status.phase!=Running
   
   # Get pod details
   kubectl describe pod <pod-name> -n market-intel-brain
   ```

2. **Create Debug Pod**
   ```bash
   # Create debug pod on same node
   ./ops/runbooks/debug-pod.sh create <pod-name>
   
   # Verify debug pod is ready
   kubectl get pod debug-<timestamp> -n market-intel-brain
   ```

3. **Network Diagnostics**
   ```bash
   # Enter debug pod
   ./ops/runbooks/debug-pod.sh interactive <pod-name>
   
   # Inside debug pod:
   ping $TARGET_POD_IP
   traceroute $TARGET_POD_IP
   netstat -an | grep :8080
   tcpdump -i any -w /tmp/capture.pcap
   ```

4. **System Diagnostics**
   ```bash
   # Inside debug pod:
   cat /host/proc/$TARGET_PID/status
   cat /host/proc/$TARGET_PID/limits
   cat /host/proc/$TARGET_PID/status | grep -E "(VmRSS|VmSize)"
   top -p $TARGET_PID
   ```

5. **Collect Logs and Events**
   ```bash
   # Collect target pod logs
   kubectl logs <pod-name> -n market-intel-brain --tail=100
   
   # Collect events
   kubectl get events -n market-intel-brain --field-selector involvedObject.name=<pod-name>
   
   # Generate debug report
   ./ops/runbooks/debug-pod.sh report <pod-name>
   ```

### Debug Pod Features

#### Network Tools
- `ping` - Test connectivity to target pod
- `traceroute` - Trace network path
- `netstat` - Show network connections
- `ss` - Socket statistics
- `tcpdump` - Packet capture
- `nslookup` - DNS resolution
- `dig` - Advanced DNS queries

#### System Tools
- `top` - Process monitoring
- `ps` - Process listing
- `lsof` - Open files
- `strace` - System call tracing
- `/proc` - Process information
- `/sys` - System information

#### Debug Commands
```bash
# Network diagnostics
kubectl exec debug-<timestamp> -n market-intel-brain -- ping $TARGET_POD_IP
kubectl exec debug-<timestamp> -n market-intel-brain -- traceroute $TARGET_POD_IP
kubectl exec debug-<timestamp> -n market-intel-brain -- netstat -an

# System diagnostics
kubectl exec debug-<timestamp> -n market-intel-brain -- cat /host/proc/$TARGET_PID/status
kubectl exec debug-<timestamp> -n market-intel-brain -- top -p $TARGET_PID
```

### Troubleshooting

#### Debug Pod Creation Fails
```bash
# Check node availability
kubectl get nodes -o wide

# Check debug pod logs
kubectl logs debug-<timestamp> -n market-intel-brain

# Check node resources
kubectl describe node <target-node>
```

#### Cannot Connect to Target Pod
```bash
# Check network policies
kubectl get networkpolicy -n market-intel-brain

# Check service endpoints
kubectl get endpoints -n market-intel-brain

# Test with different tools
kubectl exec debug-<timestamp> -n market-intel-brain -- telnet $TARGET_POD_IP 8080
```

---

## Emergency Procedures

### 🚨 System-Wide Outage

#### Immediate Response
1. **Assess Impact**
   ```bash
   # Check all pod statuses
   kubectl get pods -n market-intel-brain
   
   # Check SLO status
   curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:system:availability:rate5m"
   ```

2. **Stabilize Services**
   ```bash
   # Scale up services if needed
   kubectl scale deployment api-gateway --replicas=5 -n market-intel-brain
   kubectl scale deployment core-engine --replicas=3 -n market-intel-brain
   
   # Restart problematic services
   kubectl rollout restart deployment/api-gateway -n market-intel-brain
   ```

3. **Create Debug Pods**
   ```bash
   # Create debug pods for critical services
   ./ops/runbooks/debug-pod.sh create api-gateway-<pod-id>
   ./ops/runbooks/debug-pod.sh create core-engine-<pod-id>
   ```

### 🚨 Certificate Expiration

#### Immediate Response
1. **Check Certificate Status**
   ```bash
   # Check all certificates
   ./ops/runbooks/rotate-certs.sh check
   
   # Check expiring certificates
   kubectl get certificates -n market-intel-brain -o wide
   ```

2. **Emergency Rotation**
   ```bash
   # Force rotate expired certificates
   FORCE_FLUSH=true ./ops/runbooks/rotate-certs.sh rotate api-gateway
   
   # Monitor rotation progress
   watch -n 10 'kubectl get certificate api-gateway-tls -n market-intel-brain'
   ```

### 🚨 Redis Memory Exhaustion

#### Immediate Response
1. **Assess Memory Usage**
   ```bash
   # Check Redis memory usage
   kubectl exec -it redis-<pod-id> -n market-intel-brain -- redis-cli info memory
   
   # Check key distribution
   ./ops/runbooks/flush-redis.sh stats
   ```

2. **Emergency Cache Flush**
   ```bash
   # Flush non-critical caches
   FORCE_FLUSH=true ./ops/runbooks/flush-redis.sh flush metrics-cache
   FORCE_FLUSH=true ./ops/runbooks/flush-redis.sh flush config-cache
   ```

3. **Scale Redis**
   ```bash
   # Scale Redis cluster
   kubectl scale statefulset redis --replicas=3 -n market-intel-brain
   ```

---

## Alert Response Procedures

### 🚨 Critical Alerts (Severity: Critical)

#### Response Time: < 5 minutes

1. **Immediate Assessment**
   ```bash
   # Check alert details
   curl -s "http://localhost:9093/api/v1/alerts"
   
   # Check system status
   ./ops/cli/ops-cli redis stats
   ./ops/cli/ops-cli cert list
   ```

2. **Stabilization**
   ```bash
   # Create debug pods for affected services
   ./ops/runbooks/debug-pod.sh create <affected-pod>
   
   # Check SLO status
   curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:system:availability:rate5m"
   ```

3. **Communication**
   - Notify on-call team via PagerDuty
   - Update Slack channel with status
   - Create incident in tracking system

### ⚠️ Warning Alerts (Severity: Warning)

#### Response Time: < 30 minutes

1. **Assessment**
   ```bash
   # Check specific metrics
   curl -s "http://localhost:9090/api/v1/query?query=market_intel_brain:api_gateway:latency_p99:rate5m"
   ```

2. **Corrective Action**
   ```bash
   # Flush affected cache if needed
   ./ops/runbooks/flush-redis.sh flush <affected-cache>
   
   # Scale services if needed
   kubectl scale deployment <service> --replicas=<new-replicas> -n market-intel-brain
   ```

3. **Monitoring**
   - Monitor recovery progress
   - Update incident status
   - Document root cause

### 📊 Informational Alerts

#### Response Time: < 2 hours

1. **Documentation**
   - Update runbooks with new procedures
   - Document system changes
   - Share lessons learned

2. **Prevention**
   - Update monitoring thresholds
   - Implement preventive measures
   - Schedule regular maintenance

---

## Contact Information

### Emergency Contacts

| Role | Contact | Method |
|------|---------|--------|
| On-call Engineer | platform-team@market-intel.com | PagerDuty |
| Site Reliability | sre-team@market-intel.com | Slack #sre-alerts |
| Security Team | security@market-intel.com | Slack #security-alerts |

### Communication Channels

| Channel | Purpose |
|---------|---------|
| #market-intel-critical | Critical alerts and emergencies |
| #market-intel-warnings | Warning alerts and notifications |
| #market-intel-operations | Daily operations and maintenance |
| #market-intel-recovery | Incident recovery and post-mortem |

### Runbook Maintenance

- **Review Monthly**: Update procedures based on incident learnings
- **Test Quarterly**: Validate all automated scripts
- **Update Annually**: Refresh contact information and procedures

---

## Appendix

### Script Locations
- Certificate rotation: `./ops/runbooks/rotate-certs.sh`
- Redis operations: `./ops/runbooks/flush-redis.sh`
- Debug operations: `./ops/runbooks/debug-pod.sh`
- CLI tool: `./ops/cli/ops-cli`

### Configuration Files
- CLI config: `./ops/cli/config.yaml`
- Certificate config: `./ops/cli/certs.yaml`
- Redis config: `./ops/cli/redis.yaml`

### Backup Locations
- Certificate backups: `./backups/certs/`
- Redis backups: `./backups/redis/`
- Debug reports: `./reports/debug/`

### Monitoring Dashboards
- SLO Dashboard: http://localhost:3000/d/market-intel-brain-slo-dashboard
- System Metrics: http://localhost:3000/d/market-intel-brain-system-metrics
- Redis Dashboard: http://localhost:3000/d/market-intel-brain-redis

---

**Last Updated**: $(date)
**Version**: 1.0.0
**Maintainer**: Platform Engineering Team
