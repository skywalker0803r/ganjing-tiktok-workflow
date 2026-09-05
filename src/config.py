"""
Configuration file for Ganjing to TikTok Pipeline
"""

import os
from datetime import datetime

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
TEMP_DIR = os.path.join(PROJECT_ROOT, 'temp')
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Database configuration
DATABASE_PATH = os.path.join(DATA_DIR, 'pipeline.db')

# Video directories
RAW_VIDEO_DIR = os.path.join(TEMP_DIR, 'raw')
PROCESSED_VIDEO_DIR = os.path.join(TEMP_DIR, 'processed')

os.makedirs(RAW_VIDEO_DIR, exist_ok=True)
os.makedirs(PROCESSED_VIDEO_DIR, exist_ok=True)

# Ganjing World Configuration
GANJING_CHANNEL_URL = "https://ganjingworld.com/channel/..."  # Replace with actual channel
GANJING_VIDEO_MIN_LENGTH = 10  # seconds
GANJING_VIDEO_MAX_LENGTH = 600  # 10 minutes - videos longer than this will be skipped

# TikTok Video Configuration
TIKTOK_TARGET_RESOLUTION = (1080, 1920)  # 9:16 portrait
TIKTOK_TARGET_FPS = 30
TIKTOK_TARGET_BITRATE = "5000k"
TIKTOK_MAX_VIDEO_LENGTH = 600  # 10 minutes

# Video Processing
VIDEO_PROCESSING = {
    'format_conversion': {
        'mode': 'blur_background',  # 'blur_background' or 'center_crop'
        'background_blur_strength': 15,
        'add_watermark': False,
    },
    'quality_enhancement': {
        'enable_upscaling': False,
        'contrast_boost': 1.1,
    },
    'trim_silence': False,
}

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Content Generation Prompt
CONTENT_GENERATION_PROMPT = """
請根據以下影片標題和內容摘要，生成一個適合 TikTok 演算法的爆款標題。
要求：
1. 標題需要使用繁體中文
2. 標題要簡潔有力，能吸引點擊，建議 15-30 字
3. 需要附帶 3-5 個相關的 TikTok Hashtags（例如 #FYP #Viral #trending）
4. 返回格式：
   標題: [生成的標題]
   Hashtags: [#tag1 #tag2 #tag3 ...]

原始標題: {original_title}
內容摘要: {content_summary}
"""

# TikTok Upload Configuration
TIKTOK_UPLOAD = {
    'post_delay_min': 3,  # Minimum seconds to wait between posts
    'post_delay_max': 5,  # Maximum seconds to wait between posts
    'max_daily_posts': 3,  # Maximum posts per day
    'auto_schedule': True,
    'scheduled_times': ['12:00', '18:00'],  # Upload at these times daily
    'enable_cookies_persistence': True,
    'session_data_dir': os.path.join(DATA_DIR, 'tiktok-session'),
    'headless': False,
    'selectors': {
        'file_input': 'input[type="file"]',
        'description': '[contenteditable="true"]',
        'post_button': 'button:has-text("Post")',
        'captcha': 'iframe[src*="captcha"], [class*="captcha"]',
    },
}

# Proxy Configuration (for IP rotation)
PROXY_ENABLED = False
PROXY_LIST = []  # List of residential proxies

# Notification Configuration
NOTIFICATION = {
    'enable_telegram': False,
    'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    'enable_line': False,
    'line_token': os.getenv('LINE_BOT_TOKEN', ''),
}

# Logging Configuration
LOGGING = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': os.path.join(LOGS_DIR, f'pipeline_{datetime.now().strftime("%Y%m%d")}.log'),
}

# Risk Control & Safety
RISK_CONTROL = {
    'max_retry_attempts': 3,
    'retry_delay': 10,  # seconds
    'captcha_pause_duration': 3600,  # 1 hour
    'auto_pause_on_captcha': True,
    'max_consecutive_failures': 5,
}

# Feature Flags
FEATURES = {
    'enable_download': True,
    'enable_processing': True,
    'enable_content_generation': True,
    'enable_upload': True,
    'dry_run_mode': False,  # If True, skip actual uploads
}

# Logging setup
def setup_logging():
    """Setup logging configuration"""
    import logging
    import logging.handlers
    
    log_dir = LOGGING['log_file']
    os.makedirs(os.path.dirname(log_dir), exist_ok=True)
    
    logger = logging.getLogger('ganjing_pipeline')
    logger.setLevel(getattr(logging, LOGGING['level']))
    
    # File handler
    fh = logging.FileHandler(log_dir)
    fh.setLevel(getattr(logging, LOGGING['level']))
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, LOGGING['level']))
    
    # Formatter
    formatter = logging.Formatter(LOGGING['format'])
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


if __name__ == '__main__':
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Database Path: {DATABASE_PATH}")
    print(f"Raw Video Dir: {RAW_VIDEO_DIR}")
    print(f"Processed Video Dir: {PROCESSED_VIDEO_DIR}")
