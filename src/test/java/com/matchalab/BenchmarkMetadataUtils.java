package com.matchalab;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * Utility for generating benchmark metadata and execution summaries.
 * Focuses on creating structured JSON files for benchmark results.
 */
public class BenchmarkMetadataUtils {
    
    /**
     * Generates benchmark metadata and execution summary files.
     * Creates benchmark-metadata.json and execution-summary.json in the specified directory.
     */
    public static void generateMetadataFiles(Path benchmarkDir, Map<String, String> environment) throws IOException {
        // Create a basic metrics report from environment data
        MetricsReport report = createBasicReport(environment);
        
        // Save metadata files
        saveMetadataFiles(report, benchmarkDir);
        
        System.out.println("✅ Metadata files saved to: " + benchmarkDir);
    }
    
    /**
     * Creates a basic metrics report from environment data.
     */
    private static MetricsReport createBasicReport(Map<String, String> environment) {
        MetricsReport report = new MetricsReport();
        report.setGenerated(LocalDateTime.now().toString());
        report.setSource("Spring Boot Actuator /actuator/prometheus");
        report.setTest("Performance Benchmark");
        
        // Add environment metadata using new variable structure
        String imageName = BenchmarkTestUtils.getRequiredEnv("IMAGE_NAME");
        String gitCommit = BenchmarkTestUtils.getRequiredEnv("APP_GIT_COMMIT");
        String gitTag = BenchmarkTestUtils.getRequiredEnv("APP_GIT_TAG");
        
        // Use IMAGE_NAME directly
        String dockerImage = imageName;
        report.setDockerImage(dockerImage);
        
        // Extract artifact name from image name
        String artifactName = extractArtifactNameFromBase(imageName);
        report.setArtifactName(artifactName);
        report.setGitCommitHash(gitCommit);
        report.setTag(gitTag.isEmpty() ? "no-tag" : gitTag);
        
        return report;
    }
    
    /**
     * Saves metadata and execution summary files in the benchmark directory.
     */
    private static void saveMetadataFiles(MetricsReport report, Path benchmarkDir) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        
        // Save environment metadata in the data subdirectory
        Path envFile = benchmarkDir.resolve("data").resolve("benchmark-metadata.json");
        try (FileWriter writer = new FileWriter(envFile.toFile())) {
            writer.write(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(createEnvironmentReport(report)));
        }
        
        // Create a summary report in the data subdirectory
        Path summaryFile = benchmarkDir.resolve("data").resolve("execution-summary.json");
        try (FileWriter writer = new FileWriter(summaryFile.toFile())) {
            writer.write(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(createExecutionSummary(report)));
        }
    }
    
    
    /**
     * Creates an environment report for the benchmark run.
     */
    private static ObjectNode createEnvironmentReport(MetricsReport report) {
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode envReport = mapper.createObjectNode();
        
        envReport.put("artifactName", report.getArtifactName());
        envReport.put("gitCommitHash", report.getGitCommitHash());
        envReport.put("tag", report.getTag());
        envReport.put("dockerImage", report.getDockerImage());
        envReport.put("generated", report.getGenerated());
        envReport.put("test", report.getTest());
        
        return envReport;
    }
    
    /**
     * Creates an execution summary for the benchmark run.
     */
    private static ObjectNode createExecutionSummary(MetricsReport report) {
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode summary = mapper.createObjectNode();
        
        summary.put("executionTime", report.getGenerated());
        summary.put("testType", report.getTest());
        summary.put("source", report.getSource());
        summary.put("artifactName", report.getArtifactName());
        summary.put("gitCommitHash", report.getGitCommitHash());
        summary.put("dockerImage", report.getDockerImage());
        
        // Add performance summary (only if request observations are available)
        // Note: This will be empty when using saveRawPrometheusMetrics() instead of full parsing
        summary.put("averageResponseTime", 0.0);
        summary.put("totalRequests", 0);
        
        // Add iteration information
        String realIterations = BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_ITERATIONS");
        String warmupIterations = BenchmarkTestUtils.getRequiredEnv("AI_BENCHMARK_K6_WARMUP_ITERATIONS");
        String totalIterations = String.valueOf(Integer.parseInt(realIterations) + Integer.parseInt(warmupIterations));
        
        summary.put("totalIterations", Integer.parseInt(totalIterations));
        summary.put("warmupIterations", Integer.parseInt(warmupIterations));
        summary.put("realIterations", Integer.parseInt(realIterations));
        
        return summary;
    }
    
    /**
     * Extracts artifact name from image name.
     * Example: "ghcr.io/com.matchalab/subscription-killer-api:0.0.1-SNAPSHOT" -> "subscription-killer-api"
     */
    private static String extractArtifactNameFromBase(String baseName) {
        String[] parts = baseName.split("/");
        if (parts.length >= 2) {
            String nameWithTag = parts[1];
            String[] nameParts = nameWithTag.split(":");
            return nameParts.length >= 1 ? nameParts[0] : "unknown";
        }
        return "unknown";
    }
    
    
    /**
     * Data model for the basic metrics report.
     */
    public static class MetricsReport {
        private String generated;
        private String source;
        private String test;
        private String artifactName;
        private String gitCommitHash;
        private String tag;
        private String dockerImage;
        
        // Getters and setters
        public String getGenerated() { return generated; }
        public void setGenerated(String generated) { this.generated = generated; }
        
        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }
        
        public String getTest() { return test; }
        public void setTest(String test) { this.test = test; }
        
        public String getArtifactName() { return artifactName; }
        public void setArtifactName(String artifactName) { this.artifactName = artifactName; }
        
        public String getGitCommitHash() { return gitCommitHash; }
        public void setGitCommitHash(String gitCommitHash) { this.gitCommitHash = gitCommitHash; }
        
        public String getTag() { return tag; }
        public void setTag(String tag) { this.tag = tag; }
        
        public String getDockerImage() { return dockerImage; }
        public void setDockerImage(String dockerImage) { this.dockerImage = dockerImage; }
    }
}
