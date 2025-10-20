"""Database module"""
from .database_manager import DatabaseManager
from config.constants import DB_FILE

db = DatabaseManager(DB_FILE)
