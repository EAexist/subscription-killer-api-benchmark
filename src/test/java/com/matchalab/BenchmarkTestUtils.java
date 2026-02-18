package com.matchalab;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.Map;
import java.util.stream.Collectors;

/**
     * Utility class for benchmark test configuration and helper methods.
     * Separates concerns from the main test class to keep it focused on TestContainers setup.
     */
public class BenchmarkTestUtils {

    /**
     * Removes surrounding quotes from a value if present.
     * Handles both single and double quotes.
     * 
     * @param value The value to process
     * @return Value without surrounding quotes
     */
    private static String removeQuotes(String value) {
        if (value == null || value.isEmpty()) {
            return value;
        }

        return value.trim().replaceAll("^[\"']|[\"']$", "");
    }

    /**
     * Extracts database name from JDBC URL.
     * 
     * @param dbUrl The JDBC URL (e.g., "jdbc:postgresql://postgres:5432/subscription_killer_db")
     * @return Database name extracted from the URL
     */
    public static String extractDbName(String dbUrl) {
        if (dbUrl == null || dbUrl.isEmpty()) {
            throw new IllegalArgumentException("Database URL cannot be null or empty");
        }
        
        // Extract database name from URL like "jdbc:postgresql://postgres:5432/subscription_killer_db"
        String[] parts = dbUrl.split("/");
        if (parts.length == 0 || parts[parts.length - 1].isEmpty()) {
            throw new IllegalArgumentException("Invalid database URL format: " + dbUrl);
        }
        
        return parts[parts.length - 1];
    }

    /**
     * Extracts database name from SPRING_DATASOURCE_URL environment variable.
     * 
     * @return Database name extracted from the environment variable
     */
    public static String extractDbNameFromEnv() {
        String dbUrl = BenchmarkTestUtils.getRequiredSpringEnv("SPRING_DATASOURCE_URL");
        return extractDbName(dbUrl);
    }

    /**
     * Loads Spring Boot environment variables from a specified environment file.
     * 
     * @param envFilePath Path to the environment file (e.g., ".env.spring.benchmark")
     * @return Map of environment variable key-value pairs
     * @throws RuntimeException if file cannot be read
     */
    public static Map<String, String> loadEnvFile(String envFilePath) {
        try {
            Path envFile = Paths.get(envFilePath);
            if (!Files.exists(envFile)) {
                System.out.println("Warning: " + envFilePath + " file not found, using minimal Spring configuration");
                return Map.of("SPRING_PROFILES_ACTIVE", "benchmark");
            }
            
            return Files.lines(envFile)
                    .map(line -> line.trim())
                    .filter(line -> !line.isEmpty() && !line.startsWith("#"))
                    .map(line -> line.split("=", 2))
                    .filter(parts -> parts.length == 2)
                    .collect(Collectors.toMap(
                            parts -> parts[0].trim(),
                            parts -> {
                                String rawValue = parts[1].trim();
                                String strippedValue = removeQuotes(rawValue);
//                                System.out.printf("[loadEnvFile] Key: %s | Raw: %s -> Stripped: %s%n",
//                                        parts[0].trim(), rawValue, strippedValue);
                                return strippedValue;
                            }
                    ));
        } catch (IOException e) {
            throw new RuntimeException("Failed to load " + envFilePath + " file", e);
        }
    }

    /**
     * Loads Spring Boot environment variables from .env.spring.benchmark or custom file.
     * Uses SPRING_ENV_FILE environment variable if set, otherwise defaults to .env.spring.benchmark.
     * 
     * @return Map of Spring environment variables
     */
    public static Map<String, String> loadSpringEnvVars() {
        String envFilePath = System.getenv().getOrDefault("SPRING_ENV_FILE", ".env.spring.benchmark");
        return loadEnvFile(envFilePath);
    }

    /**
     * Gets a required Spring environment variable, prioritizing system environment variables
     * over the .env file. This allows GitHub Actions to set variables directly.
     * 
     * @param envVarName Name of the environment variable
     * @return Environment variable value
     * @throws IllegalArgumentException if environment variable is not set or empty
     */
    public static String getRequiredSpringEnv(String envVarName) {
        // First check system environment variables (GitHub Actions sets these)
        String envValue = System.getenv(envVarName);
        if (envValue != null && !envValue.trim().isEmpty()) {
            return envValue.trim();
        }
        
        // Fallback to loading from .env file (for local development)
        Map<String, String> springEnv = loadSpringEnvVars();
        String fileValue = springEnv.get(envVarName);
        if (fileValue == null || fileValue.trim().isEmpty()) {
            throw new IllegalArgumentException(envVarName + " environment variable is required but not set");
        }
        return fileValue.trim();
    }

    /**
     * Gets timeout duration from environment variable.
     * 
     * @return Duration object for timeout
     */
    public static Duration getTimeoutDuration() {
        String timeoutMinutes = System.getenv().getOrDefault("REQUEST_TIMEOUT_MINUTES", "5");
        return Duration.ofMinutes(Long.parseLong(timeoutMinutes));
    }

    /**
     * Gets a required environment variable, throwing an exception if not found.
     * 
     * @param envVarName Name of the environment variable
     * @return Environment variable value
     * @throws IllegalArgumentException if environment variable is not set or empty
     */
    public static String getRequiredEnv(String envVarName) {
        String value = System.getenv(envVarName);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(envVarName + " environment variable is required but not set");
        }
        return value;
    }
}
