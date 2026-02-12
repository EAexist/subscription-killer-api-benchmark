package com.matchalab;

import org.slf4j.LoggerFactory;
import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;

/**
 * Utility class for configuring test logging to prevent sensitive data exposure.
 * Centralizes logging configuration for benchmark tests.
 */
public class TestLoggingConfig {

    /**
     * Configures logging for benchmark tests to prevent sensitive environment variables from being exposed.
     * This should be called once in a static block of test classes.
     */
    public static void configureTestLogging() {
        boolean enableVerboseDockerLogs = Boolean.parseBoolean(
            System.getenv().getOrDefault("AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS", "false")
        );
        
        // Set the logging level for docker-java-stream
        Logger dockerLogger = (Logger) LoggerFactory.getLogger("com.github.dockerjava.zerodep.shaded.org.apache.hc.client5.http.wire");
        dockerLogger.setLevel(enableVerboseDockerLogs ? Level.DEBUG : Level.WARN);
        
        // Also set the parent logger
        Logger dockerParentLogger = (Logger) LoggerFactory.getLogger("com.github.dockerjava");
        dockerParentLogger.setLevel(enableVerboseDockerLogs ? Level.DEBUG : Level.WARN);
        
        // Disable TestContainers debug logging to prevent sensitive environment variables from being exposed
        Logger testcontainersLogger = (Logger) LoggerFactory.getLogger("org.testcontainers");
        testcontainersLogger.setLevel(Level.WARN);
        
        // Disable Docker command logging that exposes environment variables
        Logger dockerCmdLogger = (Logger) LoggerFactory.getLogger("org.testcontainers.shaded.com.github.dockerjava.core.command");
        dockerCmdLogger.setLevel(Level.WARN);
    }

    /**
     * Enables verbose Docker logging for debugging purposes.
     * WARNING: This will expose sensitive environment variables in logs.
     * Only use in secure environments.
     */
    public static void enableVerboseLogging() {
        // Set the logging level for docker-java-stream
        Logger dockerLogger = (Logger) LoggerFactory.getLogger("com.github.dockerjava.zerodep.shaded.org.apache.hc.client5.http.wire");
        dockerLogger.setLevel(Level.DEBUG);
        
        // Also set the parent logger
        Logger dockerParentLogger = (Logger) LoggerFactory.getLogger("com.github.dockerjava");
        dockerParentLogger.setLevel(Level.DEBUG);
        
        // Enable TestContainers debug logging
        Logger testcontainersLogger = (Logger) LoggerFactory.getLogger("org.testcontainers");
        testcontainersLogger.setLevel(Level.DEBUG);
        
        // Enable Docker command logging
        Logger dockerCmdLogger = (Logger) LoggerFactory.getLogger("org.testcontainers.shaded.com.github.dockerjava.core.command");
        dockerCmdLogger.setLevel(Level.DEBUG);
    }
}
