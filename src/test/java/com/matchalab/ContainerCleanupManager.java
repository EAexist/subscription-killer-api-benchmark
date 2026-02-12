package com.matchalab;

import org.testcontainers.containers.GenericContainer;

/**
 * Utility class for managing container cleanup during test execution.
 * Provides shutdown hooks to ensure containers are cleaned up on interruption.
 */
public class ContainerCleanupManager {
    
    /**
     * Registers a shutdown hook to clean up containers on Ctrl+C or abnormal termination.
     * 
     * @param containers Array of containers to cleanup
     */
    public static void registerShutdownHook(GenericContainer<?>... containers) {
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\n=== Shutdown Hook Triggered ===");
            System.out.println("Cleaning up containers...");
            
            for (GenericContainer<?> container : containers) {
                try {
                    if (container != null && container.isRunning()) {
                        String containerName = container.getClass().getSimpleName();
                        System.out.println("Stopping " + containerName + " container...");
                        container.stop();
                    }
                } catch (Exception e) {
                    System.out.println("Error stopping container: " + e.getMessage());
                }
            }
            
            System.out.println("Cleanup completed.");
        }));
    }
}
