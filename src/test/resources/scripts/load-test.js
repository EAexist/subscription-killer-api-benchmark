import http from 'k6/http';
import { check, sleep } from 'k6';

// Configuration constants
const BASE_URL = __ENV.API_BASE_URL || 'http://spring-app:8080';
const ENDPOINT = __ENV.AI_BENCHMARK_ENDPOINT || 'api/benchmark/analyze';
const TEST_ITERATIONS = parseInt(__ENV.AI_BENCHMARK_K6_ITERATIONS) || 1;
const WARMUP_ITERATIONS = parseInt(__ENV.AI_BENCHMARK_K6_WARMUP_ITERATIONS) || 0;

// Convert duration string to milliseconds (e.g., "5m" -> 300000)
function durationToMs(durationStr) {
    if (!durationStr) return 300000; // default 5 minutes
    
    const unitMultipliers = { 's': 1000, 'm': 60000, 'h': 3600000 };
    const match = durationStr.match(/^(\d+)([smh])$/);
    
    if (!match) return 300000;
    return parseInt(match[1]) * (unitMultipliers[match[2]] || 300000);
}

// Create HTTP request parameters
function createRequestParams() {
    return {
        headers: {
            'Content-Type': 'application/json',
        },
    };
}

// Execute HTTP request and log response
function executeRequest(iterationType, iterationNum, totalIterations) {
    console.log(`[${iterationType}] ${iterationType} iteration ${iterationNum}/${totalIterations}`);
    console.log("Sending POST request...");
    
    const response = http.post(`${BASE_URL}/${ENDPOINT}`, JSON.stringify({}), createRequestParams());
    console.log(`Response status: ${response.status}`);
    console.log(`Response time: ${response.timings.duration}ms`);
    
    // Validate response for test iterations only
    if (iterationType === 'TEST') {
        check(response, {
            'status is 2XX': (r) => r.status >= 200 && r.status < 300,
        });
    }
    
    return response;
}

// Log configuration details
function logConfiguration() {
    console.log('=== K6 Configuration ===');
    console.log(`Test iterations: ${TEST_ITERATIONS}`);
    console.log(`Warmup iterations: ${WARMUP_ITERATIONS}`);
    console.log(`Total iterations: ${TEST_ITERATIONS + WARMUP_ITERATIONS}`);
    console.log(`Target endpoint: ${BASE_URL}/${ENDPOINT}`);
    console.log(`Request timeout: ${__ENV.AI_BENCHMARK_REQUEST_TIMEOUT || '5m'}`);
    console.log(`Verbose Docker logs: ${__ENV.AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS || 'false'}`);
}

// K6 configuration
export let options = {
    vus: 1,
    iterations: TEST_ITERATIONS,
    thresholds: {
        http_req_failed: ['rate<1'],
        http_req_duration: [`p(100)<${durationToMs(__ENV.AI_BENCHMARK_REQUEST_TIMEOUT)}`],
    },
    timeout: __ENV.AI_BENCHMARK_REQUEST_TIMEOUT || '5m',
};

// Setup function - runs once before test iterations
export function setup() {
    logConfiguration();
    
    // Execute warmup iterations
    for (let i = 1; i <= WARMUP_ITERATIONS; i++) {
        executeRequest('WARMUP', i, WARMUP_ITERATIONS);
        sleep(0.1);
    }
}

// Main test function - runs for each test iteration
export default function () {
    const currentIteration = __ITER + 1;
    executeRequest('TEST', currentIteration, TEST_ITERATIONS);
    sleep(0.1);
}

// Handle test results
export function handleSummary(data) {
    console.log('=== Load Test Results ===');
    console.log(`Total Requests: ${data.metrics.http_reqs.count}`);
    console.log(`Successful Requests: ${data.metrics.http_reqs.count - data.metrics.http_req_failed.count}`);
    console.log(`Failed Requests: ${data.metrics.http_req_failed.count}`);
    console.log(`Error Rate: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%`);
    console.log(`Test iterations: ${TEST_ITERATIONS}`);
    console.log(`Warmup iterations: ${WARMUP_ITERATIONS}`);
    console.log(`Total iterations: ${TEST_ITERATIONS + WARMUP_ITERATIONS}`);
    console.log('test finished');
    
    return {
        'stdout': 'test finished',
        'performance-results.json': JSON.stringify(data, null, 2),
    };
}
