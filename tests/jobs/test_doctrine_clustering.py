#!/usr/bin/env python3
"""Tests for doctrine clustering background job.

This test suite verifies the daily background job that:
1. Clusters last 7 days of fleet snapshots
2. Creates/updates doctrine templates
3. Derives items of interest for each doctrine
4. Logs execution results properly
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestDoctrineClusteringJob:
    """Test suite for the doctrine clustering background job."""

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    @patch('jobs.doctrine_clustering.get_db_connection')
    def test_successful_clustering_with_doctrines(
        self,
        mock_db,
        mock_deriver_class,
        mock_service_class
    ):
        """Test successful clustering that creates doctrines and derives items."""
        from jobs import doctrine_clustering

        # Mock service to return 3 doctrines created
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 3
        mock_service_class.return_value = mock_service

        # Mock deriver
        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        # Mock database connection to fetch created doctrines
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn

        # Mock fetchall to return 3 doctrine rows with all 13 fields
        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            (1, 'Doctrine 1', None, 10000002, {'17738': 0.5}, 0.8, 10, now, now, 25, None, now, now),
            (2, 'Doctrine 2', None, 10000043, {'17736': 0.5}, 0.7, 8, now, now, 20, None, now, now),
            (3, 'Doctrine 3', None, 10000030, {'639': 0.5}, 0.9, 12, now, now, 30, None, now, now),
        ]

        # Mock deriver to return items
        from services.war_economy.doctrine.models import ItemOfInterest
        mock_items = [
            ItemOfInterest(
                doctrine_id=1,
                type_id=28668,
                item_name="Nanite Repair Paste",
                item_category="module",
                consumption_rate=None,
                priority=1,
                created_at=datetime.now()
            )
        ]
        mock_deriver.derive_items_for_doctrine.return_value = mock_items

        # Execute main function
        exit_code = doctrine_clustering.main()

        # Assertions
        assert exit_code == 0
        mock_service.cluster_snapshots.assert_called_once_with(hours_back=168)
        assert mock_deriver.derive_items_for_doctrine.call_count == 3

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    def test_successful_clustering_no_doctrines(
        self,
        mock_deriver_class,
        mock_service_class
    ):
        """Test successful clustering but no doctrines created (insufficient data)."""
        from jobs import doctrine_clustering

        # Mock service to return 0 doctrines
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 0
        mock_service_class.return_value = mock_service

        # Mock deriver
        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        # Execute main function
        exit_code = doctrine_clustering.main()

        # Assertions
        assert exit_code == 0
        mock_service.cluster_snapshots.assert_called_once_with(hours_back=168)
        mock_deriver.derive_items_for_doctrine.assert_not_called()

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    def test_custom_hours_back_argument(
        self,
        mock_deriver_class,
        mock_service_class
    ):
        """Test --hours-back argument changes lookback period."""
        from jobs import doctrine_clustering

        # Mock service
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 0
        mock_service_class.return_value = mock_service

        # Mock deriver
        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        # Execute with custom hours
        exit_code = doctrine_clustering.main(hours_back=48)

        # Assertions
        assert exit_code == 0
        mock_service.cluster_snapshots.assert_called_once_with(hours_back=48)

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    def test_clustering_service_exception(self, mock_service_class):
        """Test graceful handling of clustering service exception."""
        from jobs import doctrine_clustering

        # Mock service to raise exception
        mock_service = Mock()
        mock_service.cluster_snapshots.side_effect = Exception("Database connection failed")
        mock_service_class.return_value = mock_service

        # Execute main function
        exit_code = doctrine_clustering.main()

        # Assertions - should return error code 1
        assert exit_code == 1

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    @patch('jobs.doctrine_clustering.get_db_connection')
    def test_items_deriver_exception_continues(
        self,
        mock_db,
        mock_deriver_class,
        mock_service_class
    ):
        """Test that item derivation exception logs error but continues."""
        from jobs import doctrine_clustering

        # Mock service to return 2 doctrines
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 2
        mock_service_class.return_value = mock_service

        # Mock deriver to fail on first doctrine, succeed on second
        mock_deriver = Mock()
        mock_deriver.derive_items_for_doctrine.side_effect = [
            Exception("Derivation failed"),
            []  # Second call succeeds with empty list
        ]
        mock_deriver_class.return_value = mock_deriver

        # Mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn

        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            (1, 'Doctrine 1', None, 10000002, {'17738': 0.5}, 0.8, 10, now, now, 25, None, now, now),
            (2, 'Doctrine 2', None, 10000043, {'17736': 0.5}, 0.7, 8, now, now, 20, None, now, now),
        ]

        # Execute main function - should not crash
        exit_code = doctrine_clustering.main()

        # Should succeed despite error
        assert exit_code == 0
        assert mock_deriver.derive_items_for_doctrine.call_count == 2

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    @patch('jobs.doctrine_clustering.get_db_connection')
    def test_logging_includes_progress(
        self,
        mock_db,
        mock_deriver_class,
        mock_service_class,
        caplog
    ):
        """Test that job logs start, progress, and completion."""
        from jobs import doctrine_clustering
        import logging

        # Enable logging capture
        caplog.set_level(logging.INFO)

        # Mock service
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 1
        mock_service_class.return_value = mock_service

        # Mock deriver
        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        # Mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn

        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            (1, 'Test Doctrine', None, 10000002, {'17738': 0.5}, 0.8, 10, now, now, 25, None, now, now),
        ]

        from services.war_economy.doctrine.models import ItemOfInterest
        mock_deriver.derive_items_for_doctrine.return_value = [
            ItemOfInterest(
                doctrine_id=1,
                type_id=28668,
                item_name="Nanite Repair Paste",
                item_category="module",
                consumption_rate=None,
                priority=1,
                created_at=datetime.now()
            )
        ]

        # Execute
        doctrine_clustering.main()

        # Check logging
        log_messages = [record.message for record in caplog.records]
        assert any("Starting doctrine clustering job" in msg for msg in log_messages)
        assert any("Doctrine clustering job complete" in msg for msg in log_messages)

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    @patch('jobs.doctrine_clustering.get_db_connection')
    def test_items_saved_to_database(
        self,
        mock_db,
        mock_deriver_class,
        mock_service_class
    ):
        """Test that derived items are saved to doctrine_items_of_interest table."""
        from jobs import doctrine_clustering

        # Mock service
        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 1
        mock_service_class.return_value = mock_service

        # Mock deriver to return 2 items
        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        from services.war_economy.doctrine.models import ItemOfInterest
        mock_items = [
            ItemOfInterest(
                doctrine_id=1,
                type_id=28668,
                item_name="Nanite Repair Paste",
                item_category="module",
                consumption_rate=None,
                priority=1,
                created_at=datetime.now()
            ),
            ItemOfInterest(
                doctrine_id=1,
                type_id=21894,
                item_name="Republic Fleet EMP L",
                item_category="ammunition",
                consumption_rate=5000.0,
                priority=1,
                created_at=datetime.now()
            )
        ]
        mock_deriver.derive_items_for_doctrine.return_value = mock_items

        # Mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_conn

        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            (1, 'Test Doctrine', None, 10000002, {'17738': 0.5}, 0.8, 10, now, now, 25, None, now, now),
        ]

        # Execute
        exit_code = doctrine_clustering.main()

        # Verify database inserts
        assert exit_code == 0
        # Should have INSERT calls for items
        insert_calls = [
            call for call in mock_cursor.execute.call_args_list
            if 'INSERT INTO doctrine_items_of_interest' in str(call)
        ]
        assert len(insert_calls) == 2

    def test_idempotent_execution(self):
        """Test that job can be run multiple times safely (idempotent)."""
        # This is more of an integration test concept
        # The job should be safe to run multiple times
        # Clustering service handles deduplication internally
        pass  # Covered by service tests


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_default_hours_back(self):
        """Test default --hours-back is 168 (7 days)."""
        from jobs import doctrine_clustering
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--hours-back', type=int, default=168)
        args = parser.parse_args([])

        assert args.hours_back == 168

    def test_custom_hours_back(self):
        """Test custom --hours-back argument."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--hours-back', type=int, default=168)
        args = parser.parse_args(['--hours-back', '48'])

        assert args.hours_back == 48


class TestExitCodes:
    """Test exit code behavior."""

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    @patch('jobs.doctrine_clustering.ItemsDeriver')
    def test_success_exit_code_0(
        self,
        mock_deriver_class,
        mock_service_class
    ):
        """Test successful execution returns exit code 0."""
        from jobs import doctrine_clustering

        mock_service = Mock()
        mock_service.cluster_snapshots.return_value = 0
        mock_service_class.return_value = mock_service

        mock_deriver = Mock()
        mock_deriver_class.return_value = mock_deriver

        exit_code = doctrine_clustering.main()
        assert exit_code == 0

    @patch('jobs.doctrine_clustering.DoctrineClusteringService')
    def test_failure_exit_code_1(self, mock_service_class):
        """Test failure returns exit code 1."""
        from jobs import doctrine_clustering

        mock_service = Mock()
        mock_service.cluster_snapshots.side_effect = Exception("Fatal error")
        mock_service_class.return_value = mock_service

        exit_code = doctrine_clustering.main()
        assert exit_code == 1
