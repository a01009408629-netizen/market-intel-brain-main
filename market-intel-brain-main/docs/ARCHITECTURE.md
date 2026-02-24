# Market Intel Brain - Architecture Overview

## Project Structure

### Core Application Files
- `production_server.py` - Main production server entry point
- `api_server.py` - Full-featured FastAPI server
- `hybrid_api_server.py` - Resource-optimized server for constrained environments

### Architecture Layers (01-10)
- `01_Perception_Layer/` - Data ingestion and preprocessing
- `02_Event_Fabric/` - Event streaming and processing
- `03_Cognitive_Agents/` - AI agents for analysis
- `04_Unified_Memory_Layer/` - Data storage and retrieval
- `05_Reasoning_Orchestration/` - Decision orchestration
- `06_Identity_Isolation/` - Security and isolation
- `07_Outcome_Fusion/` - Result aggregation

### Infrastructure
- `infrastructure/` - Core infrastructure components
- `services/` - Business logic services
- `api/` - API endpoints and routes
- `k8s/` - Kubernetes deployment manifests

### Configuration
- `requirements_production.txt` - Production dependencies
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Development environment

## Entry Points

### Production
```bash
python production_server.py
```

### Development
```bash
python api_server.py
```

### Resource-Constrained
```bash
python hybrid_api_server.py
```

## Key Features
- 19+ architectural layers
- Multi-provider data integration
- Real-time processing
- Kubernetes deployment ready
- Enterprise security
- Comprehensive monitoring
