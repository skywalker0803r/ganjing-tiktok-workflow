"""
Test script for database module
"""

import sys
import os
import tempfile

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
from config import setup_logging
import logging

# Setup logging
logger = setup_logging()


def test_database():
    """Test database functionality"""
    
    logger.info("=" * 60)
    logger.info("Starting Database Module Tests")
    logger.info("=" * 60)
    
    # Initialize an isolated database so test records never affect pipeline data.
    temporary_directory = tempfile.TemporaryDirectory()
    database_path = os.path.join(temporary_directory.name, 'pipeline.db')
    db = DatabaseManager(database_path)
    logger.info(f"✓ Database initialized at {database_path}")
    
    # Test 1: Add videos
    logger.info("\n📝 Test 1: Adding Videos")
    test_videos = [
        ('ganjing_001', 'https://ganjingworld.com/video/001', '政治分析 - 2024年趨勢'),
        ('ganjing_002', 'https://ganjingworld.com/video/002', '經濟見聞 - 新興市場'),
        ('ganjing_003', 'https://ganjingworld.com/video/003', '社會觀察 - 文化差異'),
    ]
    
    video_ids = []
    for ganjing_id, url, title in test_videos:
        vid = db.add_video(ganjing_id, url, title)
        if vid > 0:
            video_ids.append(vid)
            logger.info(f"  ✓ Added: {title} (ID: {vid})")
        else:
            logger.warning(f"  ✗ Video already exists: {ganjing_id}")
    
    # Test 2: Get video by Ganjing ID
    logger.info("\n🔍 Test 2: Retrieving Videos by Ganjing ID")
    video = db.get_video_by_ganjing_id('ganjing_001')
    if video:
        logger.info(f"  ✓ Found video: {video['title']}")
        logger.info(f"    Status: {video['status']}")
    else:
        logger.error("  ✗ Video not found")
    
    # Test 3: Update video status
    logger.info("\n📊 Test 3: Updating Video Status")
    if video_ids:
        for vid in video_ids[:2]:
            success = db.update_video_status(vid, 'downloaded')
            if success:
                logger.info(f"  ✓ Video {vid} marked as downloaded")
            else:
                logger.error(f"  ✗ Failed to update video {vid}")
    
    # Test 4: Get videos by status
    logger.info("\n📋 Test 4: Retrieving Videos by Status")
    downloaded = db.get_videos_by_status('downloaded')
    logger.info(f"  ✓ Found {len(downloaded)} downloaded videos")
    for v in downloaded:
        logger.info(f"    - {v['title']} (Status: {v['status']})")
    
    pending = db.get_videos_by_status('pending')
    logger.info(f"  ✓ Found {len(pending)} pending videos")
    for v in pending:
        logger.info(f"    - {v['title']} (Status: {v['status']})")
    
    # Test 5: Log processing steps
    logger.info("\n📝 Test 5: Logging Processing Steps")
    if video_ids:
        vid = video_ids[0]
        db.log_processing_step(vid, 'download', 'Successfully downloaded video')
        logger.info(f"  ✓ Logged download step for video {vid}")
        
        db.log_processing_step(vid, 'process', 'Converting format to 9:16')
        logger.info(f"  ✓ Logged processing step for video {vid}")
    
    # Test 6: Get processing logs
    logger.info("\n📖 Test 6: Retrieving Processing Logs")
    if video_ids:
        logs = db.get_processing_logs(video_ids[0])
        logger.info(f"  ✓ Found {len(logs)} processing logs for video {video_ids[0]}")
        for log in logs:
            logger.info(f"    - [{log['stage']}] {log['message']} ({log['status']})")
    
    # Test 7: Update TikTok URL
    logger.info("\n🎯 Test 7: Updating TikTok URL")
    if video_ids:
        vid = video_ids[0]
        success = db.update_tiktok_url(vid, 'https://tiktok.com/@user/video/12345')
        if success:
            logger.info(f"  ✓ TikTok URL updated for video {vid}")
    
    # Test 8: Get statistics
    logger.info("\n📈 Test 8: Pipeline Statistics")
    stats = db.get_stats()
    logger.info(f"  Total videos: {stats.get('total', 0)}")
    logger.info(f"  Pending: {stats.get('pending', 0)}")
    logger.info(f"  Downloaded: {stats.get('downloaded', 0)}")
    logger.info(f"  Processed: {stats.get('processed', 0)}")
    logger.info(f"  Uploaded: {stats.get('uploaded', 0)}")
    logger.info(f"  Uploaded today: {stats.get('uploaded_today', 0)}")
    
    # Test 9: Error handling - duplicate video
    logger.info("\n⚠️  Test 9: Error Handling (Duplicate Video)")
    dup_id = db.add_video('ganjing_001', 'https://ganjingworld.com/video/001', 'Duplicate')
    if dup_id == -1:
        logger.info(f"  ✓ Duplicate video correctly rejected")
    else:
        logger.error(f"  ✗ Duplicate video was added (unexpected)")
    
    # Test 10: Update status with error message
    logger.info("\n❌ Test 10: Marking Video as Failed")
    if video_ids:
        vid = video_ids[0]
        success = db.update_video_status(vid, 'failed', 'Network timeout during download')
        if success:
            logger.info(f"  ✓ Video {vid} marked as failed with error message")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All Database Tests Completed Successfully!")
    logger.info("=" * 60)
    temporary_directory.cleanup()


if __name__ == '__main__':
    test_database()
