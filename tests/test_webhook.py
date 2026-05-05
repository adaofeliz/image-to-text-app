"""Tests for webhook notification utility."""

import os
import threading
import time
from unittest.mock import patch, MagicMock

import pytest
import requests

from app.queues.job_queue import process_image_job
from app.utils.webhook import send_webhook


class TestSendWebhook:
    """Test suite for send_webhook function."""

    def test_success_on_first_attempt(self):
        """Webhook succeeds on first 200 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        call_count = [0]
        lock = threading.Lock()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
            return mock_resp

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            send_webhook('http://example.com/hook', {'test': 'data'})
            for _ in range(50):
                with lock:
                    if call_count[0] >= 1:
                        break
                time.sleep(0.1)

            assert call_count[0] == 1

    def test_retry_on_500_then_success(self):
        """Retry on 500 response, then succeed on next attempt."""
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        call_count = [0]
        lock = threading.Lock()
        done = threading.Event()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
                if call_count[0] >= 2:
                    done.set()
            if call_count[0] == 1:
                return mock_fail
            return mock_ok

        sleep_calls = []
        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            with patch('app.utils.webhook.time.sleep', side_effect=track_sleep):
                send_webhook('http://example.com/hook', {'test': 'data'})
                done.wait(timeout=5.0)

                assert call_count[0] == 2
                assert len(sleep_calls) == 1
                assert 30 in sleep_calls

    def test_no_retry_on_400(self):
        """Do not retry on 4xx client errors."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        call_count = [0]
        lock = threading.Lock()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
            return mock_resp

        sleep_calls = []
        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            with patch('app.utils.webhook.time.sleep', side_effect=track_sleep):
                send_webhook('http://example.com/hook', {'test': 'data'})
                for _ in range(50):
                    with lock:
                        if call_count[0] >= 1:
                            break
                    time.sleep(0.1)

                assert call_count[0] == 1
                assert len(sleep_calls) == 0

    def test_retry_on_connection_error(self):
        """Retry on network errors."""
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        call_count = [0]
        lock = threading.Lock()
        done = threading.Event()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
                if call_count[0] >= 2:
                    done.set()
            if call_count[0] == 1:
                raise requests.ConnectionError()
            return mock_ok

        sleep_calls = []
        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            with patch('app.utils.webhook.time.sleep', side_effect=track_sleep):
                send_webhook('http://example.com/hook', {'test': 'data'})
                done.wait(timeout=5.0)

                assert call_count[0] == 2
                assert 30 in sleep_calls

    def test_max_retries_exceeded(self):
        """Give up after 10 retries (11 total attempts)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        call_count = [0]
        lock = threading.Lock()
        done = threading.Event()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
                if call_count[0] >= 11:
                    done.set()
            return mock_resp

        sleep_calls = []
        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            with patch('app.utils.webhook.time.sleep', side_effect=track_sleep):
                send_webhook('http://example.com/hook', {'test': 'data'})
                done.wait(timeout=10.0)

                # 11 total attempts (1 initial + 10 retries)
                assert call_count[0] == 11
                # sleep called 10 times (after attempts 1-10, not after attempt 11)
                assert len(sleep_calls) == 10

    def test_backoff_increases(self):
        """Backoff time increases linearly: 30s × retry_number."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        call_count = [0]
        lock = threading.Lock()
        done = threading.Event()

        def mock_post(*args, **kwargs):
            with lock:
                call_count[0] += 1
                if call_count[0] >= 11:
                    done.set()
            return mock_resp

        sleep_calls = []
        def track_sleep(duration):
            sleep_calls.append(duration)

        with patch('app.utils.webhook.requests.post', side_effect=mock_post):
            with patch('app.utils.webhook.time.sleep', side_effect=track_sleep):
                send_webhook('http://example.com/hook', {'test': 'data'})
                done.wait(timeout=10.0)

                # 10 sleeps: 30, 60, 90, ..., 300
                assert sleep_calls == [30 * i for i in range(1, 11)]

    def test_daemon_thread(self):
        """Webhook runs in a daemon thread."""
        with patch('app.utils.webhook.threading.Thread') as mock_thread:
            mock_thread.return_value = MagicMock()
            send_webhook('http://example.com/hook', {'test': 'data'})

            assert mock_thread.called
            kwargs = mock_thread.call_args[1]
            assert kwargs.get('daemon') is True


class TestProcessImageJobWebhook:
    """Integration tests for webhook in process_image_job actor."""

    def test_webhook_dispatched_on_success(self):
        """Webhook is dispatched when job succeeds."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch('app.queues.job_queue.process_image_job_sync', return_value={'content': 'hello'}):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    with patch('app.queues.job_queue.CurrentMessage') as mock_msg:
                        mock_msg.get_current_message.return_value = MagicMock(message_id='abc-123')
                        process_image_job({'image_file_path': '/tmp/test.png'})

                        time.sleep(0.5)
                        mock_send.assert_called_once()
                        url, payload = mock_send.call_args[0]
                        assert url == 'http://example.com/hook'
                        assert payload['message_id'] == 'abc-123'
                        assert payload['status'] == 'finished'
                        assert payload['result']['content'] == 'hello'

    def test_webhook_silent_skip_without_env(self):
        """No webhook dispatched when WEBHOOK_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('app.queues.job_queue.process_image_job_sync', return_value={'content': 'hello'}):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    process_image_job({'image_file_path': '/tmp/test.png'})

                    time.sleep(0.5)
                    mock_send.assert_not_called()

    def test_webhook_includes_optional_metadata(self):
        """Webhook payload includes email, session_id, filename when present."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch('app.queues.job_queue.process_image_job_sync', return_value={'content': 'hello'}):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    with patch('app.queues.job_queue.CurrentMessage') as mock_msg:
                        mock_msg.get_current_message.return_value = MagicMock(message_id='abc-123')
                        process_image_job({
                            'image_file_path': '/tmp/test.png',
                            'email': 'user@example.com',
                            'session_id': 'sess-456',
                            'filename': 'test.png'
                        })

                        time.sleep(0.5)
                        url, payload = mock_send.call_args[0]
                        assert payload['email'] == 'user@example.com'
                        assert payload['session_id'] == 'sess-456'
                        assert payload['filename'] == 'test.png'

    def test_webhook_dispatched_on_failure(self):
        """Webhook is dispatched with error payload when job fails."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch('app.queues.job_queue.process_image_job_sync', side_effect=Exception('OCR failed')):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    with patch('app.queues.job_queue.CurrentMessage') as mock_msg:
                        mock_msg.get_current_message.return_value = MagicMock(message_id='err-789')
                        with pytest.raises(Exception):
                            process_image_job({'image_file_path': '/tmp/test.png'})

                        time.sleep(0.5)
                        mock_send.assert_called_once()
                        url, payload = mock_send.call_args[0]
                        assert payload['message_id'] == 'err-789'
                        assert payload['status'] == 'failed'
                        assert payload['error'] == 'OCR failed'
                        assert payload['result'] is None

    def test_webhook_skipped_when_image_file_not_found(self):
        """No webhook dispatched when the image file does not exist."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch(
                'app.queues.job_queue.process_image_job_sync',
                side_effect=ValueError("Image file not found: /app/shared_files/tmp123.png"),
            ):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    with pytest.raises(ValueError):
                        process_image_job({'image_file_path': '/app/shared_files/tmp123.png'})

                    time.sleep(0.2)
                    mock_send.assert_not_called()

    def test_webhook_dispatched_on_other_value_error(self):
        """Webhook IS dispatched for unrelated ValueError (not a missing file)."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch(
                'app.queues.job_queue.process_image_job_sync',
                side_effect=ValueError("OCR model failed to load"),
            ):
                with patch('app.queues.job_queue.send_webhook') as mock_send:
                    with patch('app.queues.job_queue.CurrentMessage') as mock_msg:
                        mock_msg.get_current_message.return_value = MagicMock(message_id='err-000')
                        with pytest.raises(ValueError):
                            process_image_job({'image_file_path': '/tmp/exists.png'})

                        time.sleep(0.2)
                        mock_send.assert_called_once()
                        _, payload = mock_send.call_args[0]
                        assert payload['status'] == 'failed'
        """Webhook errors are caught and don't crash the actor."""
        with patch.dict(os.environ, {'WEBHOOK_URL': 'http://example.com/hook'}):
            with patch('app.queues.job_queue.process_image_job_sync', return_value={'content': 'hello'}):
                with patch('app.utils.webhook.send_webhook', side_effect=Exception('Webhook failed')):
                    with patch('app.queues.job_queue.CurrentMessage') as mock_msg:
                        mock_msg.get_current_message.return_value = MagicMock(message_id='abc-123')
                        result = process_image_job({'image_file_path': '/tmp/test.png'})
                        assert result['content'] == 'hello'
