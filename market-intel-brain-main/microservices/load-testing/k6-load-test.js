// k6 Load Testing Script for Market Intel Brain API Gateway
// Simulates high concurrent traffic to test performance and resilience

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics for detailed performance tracking
export let errorRate = new Rate('errors');
export let marketDataFetchRate = new Rate('market_data_fetch_success');
export let newsFetchRate = new Rate('news_fetch_success');
export let bufferFetchRate = new Rate('buffer_fetch_success');
export let statsFetchRate = new Rate('stats_fetch_success');
export let websocketConnectRate = new Rate('websocket_connect_success');

// Test configuration
export let options = {
  stages: [
    // Warm-up phase
    { duration: '30s', target: 100 },
    // Ramp up to 500 users
    { duration: '1m', target: 500 },
    // Hold at 500 users
    { duration: '2m', target: 500 },
    // Ramp up to 1000 users
    { duration: '1m', target: 1000 },
    // Hold at 1000 users (peak load)
    { duration: '5m', target: 1000 },
    // Ramp down to 500 users
    { duration: '1m', target: 500 },
    // Hold at 500 users
    { duration: '2m', target: 500 },
    // Cool down
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% under 500ms, 99% under 1s
    http_req_failed: ['rate<0.01'], // Error rate under 1%
    errors: ['rate<0.01'], // Custom error rate under 1%
    market_data_fetch_success: ['rate>0.95'], // 95% success rate for market data
    news_fetch_success: ['rate>0.95'], // 95% success rate for news
    buffer_fetch_success: ['rate>0.95'], // 95% success rate for buffer
    stats_fetch_success: ['rate>0.95'], // 95% success rate for stats
    websocket_connect_success: ['rate>0.90'], // 90% success rate for WebSocket
  },
  ext: {
    loadimpact: {
      projectID: 3577, // Optional: LoadImpact project ID
      name: 'Market Intel Brain Load Test',
    },
  },
};

// Base URL for the API Gateway
const BASE_URL = 'http://localhost:8080';
const API_BASE = `${BASE_URL}/api/v1`;

// Test data
const SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V'];
const NEWS_KEYWORDS = ['stock', 'market', 'trading', 'investment', 'finance'];
const DATA_SOURCES = ['yahoo_finance', 'news_api'];

// Helper function to generate random symbols
function getRandomSymbols(count) {
  const symbols = [];
  for (let i = 0; i < count; i++) {
    symbols.push(SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]);
  }
  return [...new Set(symbols)]; // Remove duplicates
}

// Helper function to generate random keywords
function getRandomKeywords(count) {
  const keywords = [];
  for (let i = 0; i < count; i++) {
    keywords.push(NEWS_KEYWORDS[Math.floor(Math.random() * NEWS_KEYWORDS.length)]);
  }
  return [...new Set(keywords)]; // Remove duplicates
}

// Test function: Health check
export function healthCheck() {
  const response = http.get(`${API_BASE}/health`, {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  });

  const success = check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
    'health check has healthy status': (r) => JSON.parse(r.body).healthy === true,
  });

  errorRate.add(!success);
  return success;
}

// Test function: Fetch market data
export function fetchMarketData() {
  const symbols = getRandomSymbols(Math.floor(Math.random() * 5) + 1);
  const sourceId = DATA_SOURCES[Math.floor(Math.random() * DATA_SOURCES.length)];

  const payload = JSON.stringify({
    symbols: symbols,
    source_id: sourceId,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  };

  const response = http.post(`${API_BASE}/market-data/fetch`, payload, params);

  const success = check(response, {
    'market data fetch status is 200': (r) => r.status === 200,
    'market data fetch response time < 500ms': (r) => r.timings.duration < 500,
    'market data fetch has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && body.market_data && body.market_data.length > 0;
      } catch (e) {
        return false;
      }
    },
  });

  marketDataFetchRate.add(success);
  errorRate.add(!success);
  return success;
}

// Test function: Fetch news data
export function fetchNewsData() {
  const keywords = getRandomKeywords(Math.floor(Math.random() * 3) + 1);
  const sourceId = DATA_SOURCES[Math.floor(Math.random() * DATA_SOURCES.length)];
  const hoursBack = Math.floor(Math.random() * 24) + 1;

  const payload = JSON.stringify({
    keywords: keywords,
    source_id: sourceId,
    hours_back: hoursBack,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  };

  const response = http.post(`${API_BASE}/news/fetch`, payload, params);

  const success = check(response, {
    'news fetch status is 200': (r) => r.status === 200,
    'news fetch response time < 500ms': (r) => r.timings.duration < 500,
    'news fetch has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && body.news_items && body.news_items.length > 0;
      } catch (e) {
        return false;
      }
    },
  });

  newsFetchRate.add(success);
  errorRate.add(!success);
  return success;
}

// Test function: Get market data buffer
export function getMarketDataBuffer() {
  const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
  const limit = Math.floor(Math.random() * 50) + 10;

  const response = http.get(`${API_BASE}/market-data/buffer?symbol=${symbol}&limit=${limit}`, {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  });

  const success = check(response, {
    'buffer fetch status is 200': (r) => r.status === 200,
    'buffer fetch response time < 200ms': (r) => r.timings.duration < 200,
    'buffer fetch has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && body.market_data;
      } catch (e) {
        return false;
      }
    },
  });

  bufferFetchRate.add(success);
  errorRate.add(!success);
  return success;
}

// Test function: Get news buffer
export function getNewsBuffer() {
  const keywords = getRandomKeywords(2).join(',');
  const limit = Math.floor(Math.random() * 30) + 5;

  const response = http.get(`${API_BASE}/news/buffer?keywords=${keywords}&limit=${limit}`, {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  });

  const success = check(response, {
    'news buffer fetch status is 200': (r) => r.status === 200,
    'news buffer fetch response time < 200ms': (r) => r.timings.duration < 200,
    'news buffer fetch has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && body.news_items;
      } catch (e) {
        return false;
      }
    },
  });

  bufferFetchRate.add(success);
  errorRate.add(!success);
  return success;
}

// Test function: Get ingestion stats
export function getIngestionStats() {
  const response = http.get(`${API_BASE}/ingestion/stats`, {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  });

  const success = check(response, {
    'stats fetch status is 200': (r) => r.status === 200,
    'stats fetch response time < 100ms': (r) => r.timings.duration < 100,
    'stats fetch has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && body.stats;
      } catch (e) {
        return false;
      }
    },
  });

  statsFetchRate.add(success);
  errorRate.add(!success);
  return success;
}

// Test function: Connect data source
export function connectDataSource() {
  const sourceId = DATA_SOURCES[Math.floor(Math.random() * DATA_SOURCES.length)];

  const payload = JSON.stringify({
    source_id: sourceId,
    api_key: '',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
    },
  };

  const response = http.post(`${API_BASE}/data-sources/connect`, payload, params);

  const success = check(response, {
    'data source connect status is 200': (r) => r.status === 200,
    'data source connect response time < 1000ms': (r) => r.timings.duration < 1000,
    'data source connect has response': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true && typeof body.connected === 'boolean';
      } catch (e) {
        return false;
      }
    },
  });

  errorRate.add(!success);
  return success;
}

// Test function: WebSocket connection (simulated)
export function testWebSocketConnection() {
  // Note: k6 doesn't support WebSocket testing directly
  // This is a placeholder that tests the WebSocket endpoint availability
  const response = http.get(`${API_BASE}/ws/market-data`, {
    headers: {
      'User-Agent': 'k6-load-test',
      'Connection': 'upgrade',
      'Upgrade': 'websocket',
    },
  });

  // WebSocket connections should return 101 (Switching Protocols) or 400 (Bad Request for HTTP)
  const success = check(response, {
    'websocket endpoint responds': (r) => r.status === 101 || r.status === 400,
    'websocket response time < 100ms': (r) => r.timings.duration < 100,
  });

  websocketConnectRate.add(success);
  errorRate.add(!success);
  return success;
}

// Main test function - distributes load across different endpoints
export default function() {
  // Weighted distribution of different types of requests
  const rand = Math.random();

  if (rand < 0.3) {
    // 30% - Fetch market data (most common operation)
    fetchMarketData();
  } else if (rand < 0.5) {
    // 20% - Fetch news data
    fetchNewsData();
  } else if (rand < 0.65) {
    // 15% - Get market data buffer
    getMarketDataBuffer();
  } else if (rand < 0.75) {
    // 10% - Get news buffer
    getNewsBuffer();
  } else if (rand < 0.85) {
    // 10% - Get ingestion stats
    getIngestionStats();
  } else if (rand < 0.95) {
    // 10% - Connect data source
    connectDataSource();
  } else {
    // 5% - Health check
    healthCheck();
  }

  // Small sleep between requests to simulate realistic user behavior
  sleep(Math.random() * 0.5 + 0.1); // 0.1 to 0.6 seconds
}

// Setup function - runs once before the test
export function setup() {
  console.log('Starting Market Intel Brain Load Test');
  console.log(`Target URL: ${BASE_URL}`);
  console.log('Test phases: Warm-up → Ramp-up → Peak → Cool-down');
}

// Teardown function - runs once after the test
export function teardown() {
  console.log('Load test completed');
  console.log('Check the k6 output for detailed performance metrics');
}
