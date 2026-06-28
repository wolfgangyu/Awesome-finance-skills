import sys
import os
import unittest

# Add skill root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from scripts.news_tools import NewsFetcher
    from scripts.database_manager import DatabaseManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

class TestNews(unittest.TestCase):
    def test_init(self):
        print("Testing NewsFetcher Initialization...")
        db = DatabaseManager(":memory:")
        tools = NewsFetcher(db)
        self.assertIsNotNone(tools)
        print("NewsFetcher Initialized.")

if __name__ == '__main__':
    unittest.main()
