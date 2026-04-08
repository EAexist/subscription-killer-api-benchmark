package com.matchalab;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.File;
import java.io.FileWriter;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;

import org.junit.jupiter.api.Test;
import org.testcontainers.containers.BindMode;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.images.PullPolicy;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

@Testcontainers
public class PerformanceBenchmarkTest {

    // Configure logging to prevent sensitive environment variables from being
    // exposed
    static {
        TestLoggingConfig.configureTestLogging();
    }

    // Docker image configuration - constructed from environment variables
    private static final String DOCKER_IMAGE = BenchmarkTestUtils.getRequiredEnv("IMAGE_NAME");

    // Shared network for communication between containers
    static Network network = Network.newNetwork();

    // 0. PostgreSQL Database Container
    @Container
    static GenericContainer<?> postgres = new GenericContainer<>("postgres:17.6")
            .withNetwork(network)
            .withNetworkAliases("postgres")
            .withExposedPorts(5432)
            .withEnv("POSTGRES_DB", BenchmarkTestUtils.extractDbNameFromEnv())
            .withEnv("POSTGRES_USER", BenchmarkTestUtils.getRequiredSpringEnv("SPRING_DATASOURCE_USERNAME"))
            .withEnv("POSTGRES_PASSWORD", BenchmarkTestUtils.getRequiredSpringEnv("SPRING_DATASOURCE_PASSWORD"))
            .waitingFor(Wait.forLogMessage(".*database system is ready to accept connections.*", 1));

    @Container
    static GenericContainer<?> springApp = new GenericContainer<>(DockerImageName.parse(DOCKER_IMAGE))
            .withImagePullPolicy(PullPolicy.defaultPolicy())
            .withNetwork(network)
            .withNetworkAliases("spring-app")
            .withExposedPorts(8080)
            .withEnv(BenchmarkTestUtils.loadSpringEnvVars())
            // Enable graceful shutdown and shutdown endpoint
            .withEnv("SERVER_SHUTDOWN", "graceful")
            .withEnv("SPRING_LIFECYCLE_TIMEOUT_PER_SHUTDOWN_PHASE", "30s")
            .withEnv("MANAGEMENT_ENDPOINT_SHUTDOWN_ENABLED", "true")
            .withEnv("MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE", "health,shutdown")
            // .withCreateContainerCmdModifier(cmd -> cmd.getHostConfig()
            // .withMemory(2 * 1024 * 1024 * 1024L) // 2GB RAM
            // .withCpuCount(4L)
            // .withMemorySwap(-1L))
            .waitingFor(Wait.forHttp("/actuator/health").forStatusCode(200))
            .dependsOn(postgres);

    // 3. Gmail API Mock Server Container
    @Container
    static GenericContainer<?> gmailMockServer = new GenericContainer<>("gmail-mock-server:latest")
            .withNetwork(network)
            .withNetworkAliases("gmail-mock-server")
            .withExposedPorts(8080)
            .withEnv("N_EMAILS_PER_REQUEST", BenchmarkTestUtils.getRequiredEnv("N_EMAILS_PER_REQUEST"))
            .withEnv("N_COMPANIES_PER_CHUNK", BenchmarkTestUtils.getRequiredEnv("N_COMPANIES_PER_CHUNK"))
            .withEnv("N_REQUESTS", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_ITERATIONS"))
            .withWorkingDirectory("/app")
            .withCommand("python", "mock_server.py")
            .waitingFor(Wait.forHttp("/health").forStatusCode(200));

    // 4. K6 Container for load testing
    @Container
    static GenericContainer<?> k6 = new GenericContainer<>("grafana/k6:0.49.0")
            .withNetwork(network)
            .withFileSystemBind("src/test/resources/scripts", "/scripts", BindMode.READ_WRITE)
            .withEnv("AI_BENCHMARK_K6_ITERATIONS", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_ITERATIONS"))
            .withEnv("AI_BENCHMARK_K6_WARMUP_ITERATIONS",
                    BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_WARMUP_ITERATIONS"))
            .withEnv("API_BASE_URL", "http://spring-app:8080")
            .withEnv("AI_BENCHMARK_ENDPOINT", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_ENDPOINT"))
            .withEnv("AI_BENCHMARK_REQUEST_TIMEOUT",
                    System.getenv().getOrDefault("AI_BENCHMARK_REQUEST_TIMEOUT", "10s"))
            .withEnv("AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS",
                    System.getenv().getOrDefault("AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS", "false"))
            .withEnv("RUN_ID",
                    System.getenv("RUN_ID"))
            .withCommand("run", "/scripts/load-test.js")
            .waitingFor(Wait.forLogMessage(".*test finished.*", 1)
                    .withStartupTimeout(BenchmarkTestUtils.getTimeoutDuration()))
            .dependsOn(springApp, gmailMockServer);

    // 3. Zipkin Container for distributed tracing
    // @Container
    // static GenericContainer<?> zipkin = new
    // GenericContainer<>("openzipkin/zipkin:latest")
    // .withNetwork(network)
    // .withNetworkAliases("zipkin")
    // .withExposedPorts(9411)
    // .waitingFor(Wait.forHttp("/health").forStatusCode(200));

    static {
        // Start log monitoring in a separate thread that waits for container to be
        // ready
        Thread logThread = new Thread(() -> {
            try {
                // Wait for k6 container to be available
                while (k6.getContainerId() == null) {
                    Thread.sleep(500);
                }

                System.out.println("=== K6 Real-time Logs ===");

                // Use docker logs to follow k6 output
                ProcessBuilder pb = new ProcessBuilder(
                        "docker", "logs", "-f", k6.getContainerId());
                pb.redirectErrorStream(true);
                Process process = pb.start();

                try (var reader = new java.io.BufferedReader(
                        new java.io.InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null && !Thread.currentThread().isInterrupted()) {
                        System.out.println("[K6] " + line);
                    }
                }
            } catch (Exception e) {
                System.out.println("Error following k6 logs: " + e.getMessage());
            }
        });

        logThread.setDaemon(true); // Don't prevent JVM shutdown
        logThread.start();

        // Register shutdown hook for container cleanup on Ctrl+C (after all containers
        // are defined)
        ContainerCleanupManager.registerShutdownHook(postgres, springApp, gmailMockServer, k6);
    }

    @Test
    void runBenchmark() {
        assertTrue(springApp.isRunning());
        // Configure Gmail API mock server if needed
        // configureGmailMockServer();

        String finalK6Logs = k6.getLogs();
        assertTrue(finalK6Logs.contains("test finished"));

        // Create benchmark directory once and reuse
        String appVersion = System.getenv().get("APP_GIT_TAG");
        String runId = System.getenv().get("RUN_ID");
        Path baseDir = Paths.get(System.getenv().getOrDefault("DATA_STORAGE_ROOT", "data-storage"));
        Path runDir;
        try {
            runDir = createBenchmarkDirectory(baseDir, appVersion, runId);
        } catch (Exception e) {
            throw new RuntimeException("Failed to create benchmark directory", e);
        }

        saveSpringBootLogs(runDir);
        saveGmailMockServerLogs(runDir);

        // Keep containers running for debugging (if enabled)
        String keepContainers = System.getenv().getOrDefault("AI_BENCHMARK_KEEP_CONTAINERS", "false");
        if ("true".equalsIgnoreCase(keepContainers)) {
            System.out.println("=== Benchmark Completed ===");
            System.out.println("Spring Boot: http://localhost:" + springApp.getMappedPort(8080));
            // System.out.println("Zipkin: http://localhost:" + zipkin.getMappedPort(9411));
            System.out.println("Containers running. Press Ctrl+C to stop.");

            long waitTime = Long.parseLong(System.getenv().getOrDefault("AI_BENCHMARK_WAIT_TIME_MS", "300000"));
            try {
                Thread.sleep(waitTime);
            } catch (InterruptedException e) {
                System.out.println("Test interrupted");
            }
        }
    }

    /**
     * Saves the raw Prometheus metrics response without parsing.
     * Creates both the raw text file and a simple JSON wrapper for easy access.
     */
    private void saveRawPrometheusMetrics(Path runDir) {
        try {
            Integer port = springApp.getMappedPort(8080);
            String prometheusUrl = String.format("http://localhost:%d/actuator/prometheus", port);

            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(prometheusUrl))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                String rawMetricsData = response.body();

                // Save as JSON wrapper for Python script consumption
                Path jsonFile = runDir.resolve("data").resolve("raw-prometheus-metrics.json");
                try (FileWriter writer = new FileWriter(jsonFile.toFile())) {
                    ObjectMapper mapper = new ObjectMapper();
                    ObjectNode wrapper = mapper.createObjectNode();
                    wrapper.put("timestamp", java.time.LocalDateTime.now().toString());
                    wrapper.put("source", prometheusUrl);
                    wrapper.put("statusCode", response.statusCode());
                    wrapper.put("contentType", "text/plain; version=0.0.4; charset=utf-8");
                    wrapper.put("rawData", rawMetricsData);
                    writer.write(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(wrapper));
                }
            } else {
                System.err.println("Failed to get raw metrics. Status: " + response.statusCode());
            }

        } catch (Exception e) {
            System.err.println("Error saving raw Prometheus metrics: " + e.getMessage());
        }
    }

    /**
     * Configures Gmail API mock server health check.
     */
    private void configureGmailMockServer() {
        try {
            Integer gmailMockServerPort = gmailMockServer.getMappedPort(8080);
            String gmailMockServerUrl = "http://localhost:" + gmailMockServerPort;

            HttpClient client = HttpClient.newHttpClient();

            // Check Gmail mock server health
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(gmailMockServerUrl + "/health"))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                System.out.println("✅ Gmail API Mock Server is healthy: " + response.body());
            } else {
                System.err.println("⚠️ Gmail Mock Server health check failed: " + response.statusCode());
            }

        } catch (Exception e) {
            System.err.println("Error checking Gmail Mock Server health: " + e.getMessage());
        }
    }

    /**
     * Saves raw Zipkin tracing data.
     */
    private void saveRawZipkinData(Path runDir) {
        try {
            // Wait for Spans to be reported and indexed
            Thread.sleep(5000);

            // Integer port = zipkin.getMappedPort(9411);
            Integer port = 9411;
            String zipkinUrl = String.format("http://localhost:%d/api/v2/traces?lookback=1200000&limit=100", port);

            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(zipkinUrl))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                String rawZipkinData = response.body();

                // Save as JSON wrapper
                Path jsonFile = runDir.resolve("data").resolve("raw-zipkin-traces.json");
                try (FileWriter writer = new FileWriter(jsonFile.toFile())) {
                    ObjectMapper mapper = new ObjectMapper();
                    ObjectNode wrapper = mapper.createObjectNode();
                    wrapper.put("timestamp", java.time.LocalDateTime.now().toString());
                    wrapper.put("source", zipkinUrl);
                    wrapper.put("statusCode", response.statusCode());
                    wrapper.put("contentType", "application/json");
                    wrapper.put("rawData", rawZipkinData);
                    writer.write(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(wrapper));
                }
            } else {
                System.err.println("Failed to get raw Zipkin data. Status: " + response.statusCode());
            }

        } catch (Exception e) {
            System.err.println("Error saving raw Zipkin data: " + e.getMessage());
        }
    }

    /**
     * Saves Gmail Mock Server container logs to benchmark directory.
     */
    private void saveGmailMockServerLogs(Path runDir) {
        saveContainerLogs(runDir, gmailMockServer, "gmail-mock-server", "gmail-mock-server-logs");
    }

    /**
     * Saves Spring Boot application logs from the container.
     */
    private void saveSpringBootLogs(Path runDir) {
        saveContainerLogs(runDir, springApp, "spring-boot-container", "spring-boot-logs");
    }

    /**
     * Utility method to save container logs in both text and JSON formats.
     * 
     * @param runDir      The benchmark directory to save logs to
     * @param container   The container to get logs from
     * @param sourceName  The source name for JSON metadata
     * @param logFileName The base filename for log files (without extension)
     */
    private void saveContainerLogs(Path runDir, GenericContainer<?> container, String sourceName, String logFileName) {
        try {
            // Get logs from the container
            String logs = container.getLogs();

            if (logs != null && !logs.isEmpty()) {
                // Save raw logs
                Path logFile = runDir.resolve(logFileName + ".txt");
                Files.createDirectories(logFile.getParent());
                Files.write(logFile, logs.getBytes(), StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);

                // Also save as JSON wrapper for consistency
                ObjectMapper mapper = new ObjectMapper();
                ObjectNode wrapper = mapper.createObjectNode();
                wrapper.put("source", sourceName);
                wrapper.put("containerId", container.getContainerId());
                wrapper.put("contentType", "text/plain");
                wrapper.put("rawData", logs);

                Path jsonFile = runDir.resolve(logFileName + ".json");
                try (FileWriter writer = new FileWriter(jsonFile.toFile())) {
                    writer.write(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(wrapper));
                }

                System.out.println("✅ " + sourceName + " logs saved to: " + logFile);
            } else {
                System.err.println("⚠️  No " + sourceName + " logs available");
            }

        } catch (Exception e) {
            System.err.println("Error saving " + sourceName + " logs: " + e.getMessage());
        }
    }

    /**
     * Creates benchmark directory structure.
     */
    private Path createBenchmarkDirectory(Path baseDir, String appVersion, String runId) throws java.io.IOException {

        // Create logs under same path as setup_logging:
        // {DATA_STORAGE_ROOT}/logs/{app_version}/{run_id}
        Path logsDir = baseDir.resolve("logs").resolve(appVersion).resolve(runId);
        java.nio.file.Files.createDirectories(logsDir);

        return logsDir;
    }

    /**
     * Generates benchmark metadata files.
     */
    private void generateBenchmarkMetadata(Path runDir) {
        try {
            BenchmarkMetadataUtils.generateMetadataFiles(runDir, System.getenv());
        } catch (Exception e) {
            System.err.println("Failed to generate benchmark metadata: " + e.getMessage());
        }
    }

    /**
     * Generates benchmark comparison using the updated Python script.
     */
    private void generateBenchmarkComparison() {
        try {
            ProcessBuilder pb = new ProcessBuilder("python", "scripts/trace_ai_benchmark_comparison.py");
            pb.directory(new File("."));
            pb.inheritIO();

            Process process = pb.start();
            int exitCode = process.waitFor();

            if (exitCode != 0) {
                System.err.println("Failed to generate benchmark comparison. Exit code: " + exitCode);
            } else {
                System.out.println("Benchmark comparison generated successfully using trace_benchmark_comparison.py");
            }
        } catch (Exception e) {
            System.err.println("Error generating benchmark comparison: " + e.getMessage());
        }
    }
}
