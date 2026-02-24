# Market Intel Brain - Configuration Guide

## Environment Variables

### Required Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Database Configuration
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:password@localhost:5432/market_intel

# API Keys (Required for data providers)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
NEWS_API_KEY=your_news_api_key

# Security
SECRETS_MASTER_KEY=your_encryption_key
JWT_SECRET_KEY=your_jwt_secret

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8000
```

### Development Environment
For development, use:
```bash
cp .env.example .env
# Edit .env with your settings
```

### Production Environment
For production, ensure all security keys are set and use strong encryption keys.
