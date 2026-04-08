import { check, sleep } from 'k6';
import http from 'k6/http';

// Configuration constants
const BASE_URL = __ENV.API_BASE_URL || 'http://spring-app:8080';
const ENDPOINT = __ENV.AI_BENCHMARK_ENDPOINT || 'api/benchmark/analyze';
const START_ENDPOINT = 'api/benchmark/start';
const TEST_ITERATIONS = parseInt(__ENV.AI_BENCHMARK_K6_ITERATIONS) || 1;
const WARMUP_ITERATIONS = parseInt(__ENV.AI_BENCHMARK_K6_WARMUP_ITERATIONS) || 0;
const REQUEST_TIMEOUT = __ENV.AI_BENCHMARK_REQUEST_TIMEOUT || '20s'

let traceparent = '';

// Convert duration string to milliseconds (e.g., "5m" -> 300000)
function durationToMs(durationStr) {

    const unitMultipliers = { 's': 1000, 'm': 60000, 'h': 3600000 };
    const match = durationStr.match(/^(\d+)([smh])$/);
    return parseInt(match[1]) * (unitMultipliers[match[2]] || 300000);
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Initialize benchmark by calling /start endpoint
function initializeBenchmark() {
    console.log('Initializing benchmark...');

    const runId = __ENV.RUN_ID;
    if (!runId) {
        console.error('RUN_ID environment variable is not set');
        throw new Error('RUN_ID environment variable is required');
    }
    console.log(`Using runId: ${runId}`);

    // Call /start endpoint
    const startUrl = `${BASE_URL}/${START_ENDPOINT}?runId=${encodeURIComponent(runId)}`;
    const startResponse = http.post(startUrl, '', { timeout: REQUEST_TIMEOUT });

    console.log(`Start response status: ${startResponse.status}`);

    if (startResponse.status !== 200) {
        console.error(`Failed to initialize benchmark (HTTP ${startResponse.status})`);
        console.error(`Response body: ${startResponse.body}`);
        throw new Error('Benchmark initialization failed');
    }

    // Extract traceparent from response
    try {
        const responseData = JSON.parse(startResponse.body);
        traceparent = responseData.traceparent;

        if (!traceparent || traceparent === 'null' || traceparent === '') {
            console.error('Failed to extract traceparent from benchmark start response');
            console.error(`Response body: ${startResponse.body}`);
            throw new Error('Traceparent extraction failed');
        }

        console.log(`Benchmark initialized with runId: ${runId}, traceparent: ${traceparent}`);
    } catch (e) {
        console.error('Error parsing start response:', e);
        console.error(`Response body: ${startResponse.body}`);
        throw new Error('Failed to parse start response');
    }
}

// Create HTTP request parameters with unique user ID and iteration index
function createRequestParams(iterationNum) {
    const userId = generateUUID();
    return {
        headers: {
            'Content-Type': 'application/json',
            'X-Benchmark-User-Id': userId,
            'X-Benchmark-Index': iterationNum.toString(),
            'traceparent': traceparent,
        },
    };
}

// Execute HTTP request and log response
function executeRequest(iterationType, iterationNum, totalIterations) {
    console.log(`[${iterationType}] ${iterationType} iteration ${iterationNum}/${totalIterations}`);
    console.log("Sending POST request...");

    const requestParams = createRequestParams(iterationNum);
    requestParams.timeout = REQUEST_TIMEOUT
    const userId = requestParams.headers['X-Benchmark-User-Id'];
    console.log(`Generated User ID: ${userId}`);

    const response = http.post(`${BASE_URL}/${ENDPOINT}`, JSON.stringify({}), requestParams);
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
    console.log(`Request timeout: ${REQUEST_TIMEOUT}`);
    console.log(`Verbose Docker logs: ${__ENV.AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS || 'false'}`);
}

// K6 configuration
export let options = {
    vus: 1,
    iterations: TEST_ITERATIONS,
    thresholds: {
        http_req_failed: ['rate<1'],
        http_req_duration: [`p(100)<${durationToMs(REQUEST_TIMEOUT)}`],
    },
};

// Setup function - runs once before test iterations
export function setup() {
    logConfiguration();

    // Initialize benchmark by calling /start endpoint
    initializeBenchmark();

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

    // After last test iteration, wait for Langfuse to flush observations
    if (currentIteration === TEST_ITERATIONS) {
        const flushWaitTime = parseInt(__ENV.LANGFUSE_FLUSH_WAIT_SECONDS) || 10;
        console.log(`Waiting ${flushWaitTime}s for observations to flush to Langfuse...`);
        sleep(flushWaitTime);
    }

    sleep(0.1);
}

// Handle test results
export function handleSummary(data) {
    console.log('=== Load Test Results ===');
    console.log(`Total iterations: ${TEST_ITERATIONS + WARMUP_ITERATIONS}`);
    console.log(`Warmup iterations: ${WARMUP_ITERATIONS}`);
    console.log(`Test iterations: ${TEST_ITERATIONS}`);
    console.log(`Total Requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`Successful Requests: ${data.metrics.http_reqs.values.count - data.metrics.http_req_failed.values.count}`);
    console.log(`Failed Requests: ${data.metrics.http_req_failed.values.count}`);
    console.log(`Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%`);

    // Initiate graceful Spring Boot shutdown
    console.log('🔄 Initiating graceful Spring Boot shutdown...');
    const shutdownUrl = `${BASE_URL}/actuator/shutdown`;
    const shutdownResponse = http.post(shutdownUrl, '', {
        timeout: '10s',
        headers: { 'Content-Type': 'application/json' }
    });

    if (shutdownResponse.status === 200) {
        console.log('✅ Spring Boot shutdown initiated successfully');
    } else {
        console.error(`⚠️ Failed to initiate Spring Boot shutdown. Status: ${shutdownResponse.status}`);
        console.error(`Response: ${shutdownResponse.body}`);
    }

    console.log('test finished');

    return {
        'stdout': 'test finished',
        'performance-results.json': JSON.stringify(data, null, 2),
    };
}
