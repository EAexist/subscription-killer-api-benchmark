package com.matchalab;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.BindMode;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.images.PullPolicy;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.io.File;
import java.io.FileWriter;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

@Testcontainers
public class PerformanceBenchmarkTest {

    // Configure logging to prevent sensitive environment variables from being exposed
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


    // 3. Zipkin Container for distributed tracing
    @Container
    static GenericContainer<?> zipkin = new GenericContainer<>("openzipkin/zipkin:latest")
            .withNetwork(network)
            .withNetworkAliases("zipkin")
            .withExposedPorts(9411)
            .waitingFor(Wait.forHttp("/health").forStatusCode(200));

    // 1. Spring Boot App Container
    @Container
    static GenericContainer<?> springApp = new GenericContainer<>(DockerImageName.parse(DOCKER_IMAGE))
            .withImagePullPolicy(PullPolicy.defaultPolicy())
            .withNetwork(network)
            .withNetworkAliases("spring-app")
            .withExposedPorts(8080)
            .withEnv(BenchmarkTestUtils.loadSpringEnvVars())
            .withEnv("SPRING_ZIPKIN_BASE_URL", "http://zipkin:9411")
            .waitingFor(Wait.forHttp("/actuator/health").forStatusCode(200))
            .dependsOn(postgres, zipkin);

    // 2. K6 Container for load testing
    @Container
    static GenericContainer<?> k6 = new GenericContainer<>("grafana/k6:0.49.0")
            .withNetwork(network)
            .withFileSystemBind("src/test/resources/scripts", "/scripts", BindMode.READ_WRITE)
            .withEnv("AI_BENCHMARK_K6_ITERATIONS", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_ITERATIONS"))
            .withEnv("AI_BENCHMARK_K6_WARMUP_ITERATIONS", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_WARMUP_ITERATIONS"))
            .withEnv("API_BASE_URL", "http://spring-app:8080")
            .withEnv("AI_BENCHMARK_ENDPOINT", BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_ENDPOINT"))
            .withEnv("AI_BENCHMARK_REQUEST_TIMEOUT", System.getenv().getOrDefault("AI_BENCHMARK_REQUEST_TIMEOUT", "5m"))
            .withEnv("AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS", System.getenv().getOrDefault("AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS", "false"))
            .withCommand("run", "/scripts/load-test.js")
            .waitingFor(Wait.forLogMessage(".*test finished.*", 1).withStartupTimeout(BenchmarkTestUtils.getTimeoutDuration()))
            .dependsOn(springApp);

    static {
        // Start log monitoring in a separate thread that waits for container to be ready
        Thread logThread = new Thread(() -> {
            try {
                // Wait for k6 container to be available
                while (k6.getContainerId() == null) {
                    Thread.sleep(500);
                }
                
                System.out.println("=== K6 Real-time Logs ===");
                
                // Use docker logs to follow k6 output
                ProcessBuilder pb = new ProcessBuilder(
                    "docker", "logs", "-f", k6.getContainerId()
                );
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
        
        // Register shutdown hook for container cleanup on Ctrl+C (after all containers are defined)
        ContainerCleanupManager.registerShutdownHook(postgres, springApp, k6, zipkin);
    }

    @Test
    void runBenchmark() {
        assertTrue(springApp.isRunning());
        
        String finalK6Logs = k6.getLogs();
        assertTrue(finalK6Logs.contains("test finished"));
        
        // Create benchmark directory once and reuse
        Path benchmarkDir;
        try {
            benchmarkDir = createBenchmarkDirectory();
        } catch (Exception e) {
            throw new RuntimeException("Failed to create benchmark directory", e);
        }
        
        saveRawPrometheusMetrics(benchmarkDir);
        saveRawZipkinData(benchmarkDir);
        generateBenchmarkMetadata(benchmarkDir);
        generateBenchmarkComparison();
        
        // Keep containers running for log inspection (if enabled)
        String keepContainers = System.getenv().getOrDefault("AI_BENCHMARK_KEEP_CONTAINERS", "false");
        if ("true".equalsIgnoreCase(keepContainers)) {
            System.out.println("=== Benchmark Completed ===");
            System.out.println("Spring Boot: http://localhost:" + springApp.getMappedPort(8080));
            System.out.println("Zipkin: http://localhost:" + zipkin.getMappedPort(9411));
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
    private void saveRawPrometheusMetrics(Path benchmarkDir) {
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
                Path jsonFile = benchmarkDir.resolve("data").resolve("raw-prometheus-metrics.json");
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
     * Saves raw Zipkin tracing data.
     */
    private void saveRawZipkinData(Path benchmarkDir) {
        try {
            // Wait for Spans to be reported and indexed
            Thread.sleep(5000);

            Integer port = zipkin.getMappedPort(9411);
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
                Path jsonFile = benchmarkDir.resolve("data").resolve("raw-zipkin-traces.json");
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
     * Creates benchmark directory structure.
     */
    private Path createBenchmarkDirectory() throws java.io.IOException {
        String gitCommitHash = System.getenv().getOrDefault("APP_GIT_COMMIT", "unknown");
        String timestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss"));
        
        Path baseDir = java.nio.file.Paths.get("results", "ai-benchmark", gitCommitHash, timestamp);
        java.nio.file.Files.createDirectories(baseDir);
        
        java.nio.file.Files.createDirectories(baseDir.resolve("data"));
        java.nio.file.Files.createDirectories(baseDir.resolve("reports"));
        java.nio.file.Files.createDirectories(baseDir.resolve("logs"));
        java.nio.file.Files.createDirectories(baseDir.resolve("artifacts"));
        
        return baseDir;
    }
    
    /**
     * Generates benchmark metadata files.
     */
    private void generateBenchmarkMetadata(Path benchmarkDir) {
        try {
            BenchmarkMetadataUtils.generateMetadataFiles(benchmarkDir, System.getenv());
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
