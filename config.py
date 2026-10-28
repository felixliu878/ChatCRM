# Configuration settings for ChatCRM
# All credentials are read from environment variables (see .env.example).
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'database': os.getenv('DB_NAME', 'chatcrm'),
    'user': os.getenv('DB_USER', ''),
    'password': os.getenv('DB_PASSWORD', ''),
    'charset': 'utf8mb4'
}

# DeepSeek V3 API Configuration
DEEPSEEK_CONFIG = {
    'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
    'base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
    'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
}

# Application Settings
APP_CONFIG = {
    'max_retries': 3,
    'timeout': 30,
    'debug': False
}
