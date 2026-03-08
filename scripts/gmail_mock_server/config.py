import json
import os


def get_latest_data_file() -> str:
    base_dir = os.getenv("DATASET_PATH", "./scripts/gmail_mock_server/dataset")
    emails_dir = os.path.join(base_dir, "data/emails")

    latest_json_path = os.path.join(emails_dir, "latest.json")

    if not os.path.exists(latest_json_path):
        raise FileNotFoundError(
            f"Critical: @latest.json not found at {latest_json_path}"
        )

    with open(latest_json_path, "r") as f:
        latest_info = json.load(f)

    relative_path = latest_info["relative_path"]
    samples_path = os.path.normpath(os.path.join(emails_dir, relative_path))

    # 3. Verify the actual data file exists before returning
    final_path = samples_path.replace("\\", "/")
    if not os.path.exists(final_path):
        raise FileNotFoundError(
            f"Critical: Data file defined in @latest.json does not exist at {final_path}"
        )

    return final_path


class Settings:
    """Application configuration settings."""

    def __init__(self):
        # Message selection configuration

        # Distribution configuration
        # self.default_distribution_field: DistributionField = DistributionField.SENDER_EMAIL
        # self.default_distribution_type: DistributionType = DistributionType.UNIFORM

        # Data configuration - dynamically find latest version
        self.data_file_path: str = get_latest_data_file()
        self.n_emails_per_request: int = 100

        # Server configuration
        self.host: str = "0.0.0.0"
        self.port: int = 8080

        # Logging configuration
        self.enable_debug_logging: bool = False


# Global settings instance
settings = Settings()

# class DistributionField(str, Enum):
#     """Fields available for distribution-based message selection."""
#     SENDER_EMAIL = "senderEmail"
#     SENDER_NAME = "senderName"
#     SUBJECT = "subject"
#     CATEGORY = "category"

# class DistributionType(str, Enum):
#     """Types of distribution available for message selection."""
#     UNIFORM = "uniform"
#     WEIGHTED = "weighted"
#     RANDOM = "random"
