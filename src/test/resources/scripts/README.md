# K6 Load Testing Scripts

This directory contains K6 performance testing scripts used by the Testcontainers benchmark.

## Scripts

### `load-test.js`
A comprehensive load testing script that simulates realistic user traffic patterns.

#### Features:
- **Gradual ramp-up/down** to avoid shocking the system
- **Multiple API endpoints** testing (health check, GET, POST)
- **Custom metrics** for error tracking
- **Thresholds** for performance SLAs
- **Detailed summary** reporting

#### Test Stages:
1. **Warm-up**: 2 minutes ramping to 10 users
2. **Steady Load**: 5 minutes at 10 users
3. **Peak Load**: 2 minutes ramping to 50 users
4. **Sustained Peak**: 5 minutes at 50 users
5. **Cool-down**: 2 minutes ramping down to 0 users

#### Performance Thresholds:
- **Response Time**: 95th percentile < 500ms
- **Error Rate**: < 10%
- **Health Check**: < 200ms response time

## Configuration

The script automatically uses the Spring Boot app URL from the Testcontainers network:
- Default: `http://spring-app:8080`
- Can be overridden with `API_BASE_URL` environment variable

## Usage

The script is automatically executed by the PerformanceBenchmarkTest using Testcontainers.

To run manually (for development):
```bash
# Set the API base URL
export API_BASE_URL="http://localhost:8080"

# Run the script
k6 run src/test/resources/scripts/load-test.js
```

## Customization

### Adding New Endpoints
1. Add new HTTP requests in the `default function()`
2. Include appropriate `check()` assertions
3. Add error tracking with `errorRate.add(!ok)`
4. Update tags for better reporting

### Modifying Load Pattern
Edit the `stages` array in the `options` object:
```javascript
stages: [
    { duration: '1m', target: 5 },   // 5 users for 1 minute
    { duration: '3m', target: 20 },  // Ramp to 20 users
    // Add more stages as needed
]
```

### Adjusting Thresholds
Modify the `thresholds` object based on your SLA requirements:
```javascript
thresholds: {
    http_req_duration: ['p(95)<300'], // Stricter 300ms requirement
    http_req_failed: ['rate<0.05'],   // Stricter 5% error rate
}
```

## Output

The test generates:
- **Console output** with real-time metrics
- **JSON summary** saved as `performance-summary.json`
- **Detailed metrics** for analysis and trending
