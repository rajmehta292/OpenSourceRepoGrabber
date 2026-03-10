import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import requests

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ollama_client import OllamaClient

class TestOllamaClientHardening(unittest.TestCase):
    def setUp(self):
        self.client = OllamaClient(base_url="http://localhost:11434", model="test-model")

    @patch('requests.Session.post')
    def test_retry_on_server_error(self, mock_post):
        # Simulate 500 error twice, then success
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Internal Server Error"
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "Success after retry"}
        
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        # We need to mock time.sleep so the test runs fast
        with patch('time.sleep', return_value=None):
            result = self.client._generate("Hello")
            
        self.assertEqual(result, "Success after retry")
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.Session.post')
    def test_retry_on_connection_error(self, mock_post):
        # Simulate ConnectionError once, then success
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "Success after connection fix"}
        
        mock_post.side_effect = [requests.exceptions.ConnectionError("Failed"), mock_response_success]
        
        with patch('time.sleep', return_value=None):
            result = self.client._generate("Hello")
            
        self.assertEqual(result, "Success after connection fix")
        self.assertEqual(mock_post.call_count, 2)

    @patch('requests.Session.post')
    def test_final_failure_after_retries(self, mock_post):
        # Simulate constant 500 error
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Permanent Error"
        
        mock_post.return_value = mock_response_fail
        
        with patch('time.sleep', return_value=None):
            result = self.client._generate("Hello", retries=2)
            
        self.assertTrue(result.startswith("Error: Ollama error: 500"))
        self.assertEqual(mock_post.call_count, 2)

if __name__ == "__main__":
    unittest.main()
