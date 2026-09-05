"""
Database Module for Ganjing to TikTok Pipeline
Manages SQLite database for tracking processed videos
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pipeline.db')


class DatabaseManager:
    """Manages SQLite database for video tracking"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ganjing_id TEXT UNIQUE NOT NULL,
                ganjing_url TEXT,
                title TEXT,
                status TEXT DEFAULT 'pending',
                downloaded_at TIMESTAMP,
                processed_at TIMESTAMP,
                content_generated_at TIMESTAMP,
                uploaded_at TIMESTAMP,
                tiktok_url TEXT,
                tiktok_title TEXT,
                tiktok_hashtags TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create processing log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                stage TEXT,
                message TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        ''')

        self._ensure_column(cursor, 'videos', 'tiktok_title', 'TEXT')
        self._ensure_column(cursor, 'videos', 'tiktok_hashtags', 'TEXT')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ganjing_id ON videos(ganjing_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON videos(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON videos(created_at)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_video(self, ganjing_id: str, ganjing_url: str, title: str) -> int:
        """
        Add new video to database
        
        Args:
            ganjing_id: Unique ID from Ganjing World
            ganjing_url: URL to video on Ganjing World
            title: Video title
            
        Returns:
            Video ID if successful, -1 if video already exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO videos (ganjing_id, ganjing_url, title, status)
                VALUES (?, ?, ?, 'pending')
            ''', (ganjing_id, ganjing_url, title))
            
            conn.commit()
            video_id = cursor.lastrowid
            logger.info(f"Added video: {ganjing_id} (ID: {video_id})")
            return video_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"Video {ganjing_id} already exists in database")
            return -1
        finally:
            conn.close()
    
    def get_video_by_ganjing_id(self, ganjing_id: str) -> Optional[dict]:
        """
        Get video record by Ganjing ID
        
        Args:
            ganjing_id: Ganjing World video ID
            
        Returns:
            Video record as dict or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM videos WHERE ganjing_id = ?', (ganjing_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_dict(row, cursor.description)
        return None
    
    def get_videos_by_status(self, status: str, limit: int = 100) -> List[dict]:
        """
        Get videos by status
        
        Args:
            status: Video status (pending, downloaded, processed, uploaded, failed)
            limit: Maximum number of records to return
            
        Returns:
            List of video records
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM videos WHERE status = ?
            ORDER BY created_at ASC
            LIMIT ?
        ''', (status, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def update_video_status(self, video_id: int, status: str, 
                          error_message: str = None) -> bool:
        """
        Update video status
        
        Args:
            video_id: Video record ID
            status: New status
            error_message: Optional error message if status is 'failed'
            
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if status == 'downloaded':
                cursor.execute('''
                    UPDATE videos SET status = ?, downloaded_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, datetime.now(), video_id))
            elif status == 'processed':
                cursor.execute('''
                    UPDATE videos SET status = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, datetime.now(), video_id))
            elif status == 'content_generated':
                cursor.execute('''
                    UPDATE videos SET status = ?, content_generated_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, datetime.now(), video_id))
            elif status == 'uploaded':
                cursor.execute('''
                    UPDATE videos SET status = ?, uploaded_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, datetime.now(), video_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE videos SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, video_id))
            else:
                cursor.execute('''
                    UPDATE videos SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, video_id))
            
            conn.commit()
            logger.info(f"Updated video {video_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update video {video_id}: {e}")
            return False
        finally:
            conn.close()
    
    def update_tiktok_url(self, video_id: int, tiktok_url: str) -> bool:
        """
        Update TikTok URL after successful upload
        
        Args:
            video_id: Video record ID
            tiktok_url: URL of uploaded video on TikTok
            
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE videos SET tiktok_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (tiktok_url, video_id))
            
            conn.commit()
            logger.info(f"Updated TikTok URL for video {video_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update TikTok URL for video {video_id}: {e}")
            return False
        finally:
            conn.close()

    def update_generated_content(self, video_id: int, title: str, hashtags: str) -> bool:
        """Save generated TikTok copy and mark the video ready for upload."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE videos
                SET tiktok_title = ?, tiktok_hashtags = ?, status = ?,
                    content_generated_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (title, hashtags, 'content_generated', datetime.now(), video_id))
            conn.commit()
            return cursor.rowcount == 1
        except Exception as e:
            logger.error(f"Failed to save generated content for video {video_id}: {e}")
            return False
        finally:
            conn.close()
    
    def log_processing_step(self, video_id: int, stage: str, 
                           message: str, status: str = 'success') -> bool:
        """
        Log processing step
        
        Args:
            video_id: Video record ID
            stage: Processing stage (download, process, generate_content, upload)
            message: Log message
            status: Status of the step (success, failure, warning)
            
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO processing_logs (video_id, stage, message, status)
                VALUES (?, ?, ?, ?)
            ''', (video_id, stage, message, status))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log processing step: {e}")
            return False
        finally:
            conn.close()
    
    def get_processing_logs(self, video_id: int) -> List[dict]:
        """
        Get processing logs for a video
        
        Args:
            video_id: Video record ID
            
        Returns:
            List of log records
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM processing_logs
            WHERE video_id = ?
            ORDER BY created_at DESC
        ''', (video_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def get_stats(self) -> dict:
        """
        Get pipeline statistics
        
        Returns:
            Dictionary with statistics
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by status
        cursor.execute('SELECT status, COUNT(*) FROM videos GROUP BY status')
        for status, count in cursor.fetchall():
            stats[status] = count
        
        # Total videos
        cursor.execute('SELECT COUNT(*) FROM videos')
        stats['total'] = cursor.fetchone()[0]
        
        # Today's uploads
        cursor.execute('''
            SELECT COUNT(*) FROM videos 
            WHERE uploaded_at >= date('now')
        ''')
        stats['uploaded_today'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

    @staticmethod
    def _ensure_column(cursor, table: str, column: str, definition: str):
        """Add a column when opening databases created by earlier versions."""
        cursor.execute(f'PRAGMA table_info({table})')
        columns = {row[1] for row in cursor.fetchall()}
        if column not in columns:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
    
    @staticmethod
    def _row_to_dict(row: Tuple, description) -> dict:
        """Convert database row to dictionary"""
        return {
            description[i][0]: row[i]
            for i in range(len(description))
        }
    
    def cleanup(self):
        """Close database connection"""
        pass


# Convenience functions
_db_manager = None


def get_db_manager():
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database():
    """Initialize database"""
    return get_db_manager()
