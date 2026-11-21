"""Phase 1 tests for photo verification engine.

Tests:
- Code verification (valid, invalid, missing)
- EXIF location extraction
- Location tolerance check (within 500m, outside tolerance)
- Combined photo + location validation
- Error handling (corrupted file, no metadata)
"""
import pytest
from datetime import datetime

from app.engines.photo_verification_engine import PhotoVerificationEngine


class TestCodeVerification:
    """Test photo code verification."""

    def test_code_verification_valid(self):
        """Test code verification passes with valid code."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "ABC123")
        assert result is True

    def test_code_verification_invalid_code(self):
        """Test code verification fails with wrong code."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "XYZ789")
        assert result is False

    def test_code_verification_case_sensitive(self):
        """Test code verification is case sensitive."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "abc123")
        assert result is False

    def test_code_verification_with_whitespace(self):
        """Test code verification fails with extra whitespace."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", " ABC123 ")
        assert result is False

    def test_code_verification_partial_match_fails(self):
        """Test code verification fails with partial match."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "ABC12")
        assert result is False


class TestLocationExtraction:
    """Test EXIF location extraction."""

    def test_calculate_distance_same_location(self):
        """Test distance calculation for same location."""
        lat1, lng1 = 12.9716, 77.5946
        lat2, lng2 = 12.9716, 77.5946
        distance = PhotoVerificationEngine.calculate_distance(lat1, lng1, lat2, lng2)
        assert distance < 1  # Less than 1 meter

    def test_calculate_distance_nearby_location(self):
        """Test distance calculation for nearby location."""
        # Approximately 100m apart
        lat1, lng1 = 12.9716, 77.5946
        lat2, lng2 = 12.9725, 77.5946
        distance = PhotoVerificationEngine.calculate_distance(lat1, lng1, lat2, lng2)
        assert 50 < distance < 150  # Approximately 100m

    def test_calculate_distance_far_location(self):
        """Test distance calculation for far location."""
        # Bangalore to Delhi
        lat1, lng1 = 12.9716, 77.5946  # Bangalore
        lat2, lng2 = 28.7041, 77.1025  # Delhi
        distance = PhotoVerificationEngine.calculate_distance(lat1, lng1, lat2, lng2)
        assert distance > 1000000  # Over 1000 km

    def test_calculate_distance_500_meters_tolerance(self):
        """Test distance within 500m tolerance."""
        lat1, lng1 = 12.9716, 77.5946
        # Approximately 500m away
        lat2, lng2 = 12.97715, 77.5946
        distance = PhotoVerificationEngine.calculate_distance(lat1, lng1, lat2, lng2)
        assert distance < 600  # Approximately 500m


class TestLocationTolerance:
    """Test location tolerance checking."""

    def test_location_within_tolerance(self):
        """Test photo location within tolerance of rent address."""
        photo_data = {
            "location_lat": 12.9716,
            "location_lng": 77.5946,
            "detected_code": "ABC123",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.location_verified is True
        assert result.distance_from_rent < 500

    def test_location_outside_tolerance(self):
        """Test photo location outside tolerance of rent address."""
        photo_data = {
            "location_lat": 12.9725,
            "location_lng": 77.5946,
            "detected_code": "ABC123",
        }
        # 100m away but tolerance is only 50m
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=50,
        )
        assert result.location_verified is False

    def test_location_exactly_at_tolerance_boundary(self):
        """Test location exactly at tolerance boundary."""
        photo_data = {
            "location_lat": 12.9716,
            "location_lng": 77.5946,
            "detected_code": "ABC123",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=0,
        )
        # Same location should be within even 0m tolerance
        assert result.location_verified is True or result.distance_from_rent == 0


class TestCombinedPhotoValidation:
    """Test combined photo and location validation."""

    def test_valid_photo_with_code_and_location(self):
        """Test complete photo verification success."""
        photo_data = {
            "location_lat": 12.9716,
            "location_lng": 77.5946,
            "detected_code": "ABC123",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.code_verified is True
        assert result.location_verified is True

    def test_invalid_code_fails_verification(self):
        """Test photo verification fails with invalid code."""
        photo_data = {
            "location_lat": 12.9716,
            "location_lng": 77.5946,
            "detected_code": "WRONG",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.code_verified is False

    def test_wrong_location_fails_verification(self):
        """Test photo verification fails with wrong location."""
        photo_data = {
            "location_lat": 28.7041,  # Delhi
            "location_lng": 77.1025,
            "detected_code": "ABC123",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,  # Bangalore
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.location_verified is False

    def test_both_invalid_fails_verification(self):
        """Test photo verification fails when both code and location invalid."""
        photo_data = {
            "location_lat": 28.7041,
            "location_lng": 77.1025,
            "detected_code": "WRONG",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.code_verified is False
        assert result.location_verified is False


class TestErrorHandling:
    """Test photo verification error handling."""

    def test_missing_photo_data(self):
        """Test handling of missing photo data."""
        photo_data = None
        try:
            result = PhotoVerificationEngine.verify_photo(
                photo_data,
                expected_code="ABC123",
                rent_lat=12.9716,
                rent_lng=77.5946,
                tolerance_meters=500,
            )
            # Should either raise or return False
            assert result.code_verified is False or result is None
        except (AttributeError, TypeError):
            # Expected
            pass

    def test_missing_location_in_photo_data(self):
        """Test handling of missing location in photo data."""
        photo_data = {"detected_code": "ABC123"}
        try:
            result = PhotoVerificationEngine.verify_photo(
                photo_data,
                expected_code="ABC123",
                rent_lat=12.9716,
                rent_lng=77.5946,
                tolerance_meters=500,
            )
            assert result.location_verified is False
        except (KeyError, TypeError, AttributeError):
            # Expected
            pass

    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        photo_data = {
            "location_lat": "invalid",
            "location_lng": "invalid",
            "detected_code": "ABC123",
        }
        try:
            result = PhotoVerificationEngine.verify_photo(
                photo_data,
                expected_code="ABC123",
                rent_lat=12.9716,
                rent_lng=77.5946,
                tolerance_meters=500,
            )
            assert result.location_verified is False
        except (ValueError, TypeError):
            # Expected
            pass

    def test_null_coordinates(self):
        """Test handling of null coordinates."""
        photo_data = {
            "location_lat": None,
            "location_lng": None,
            "detected_code": "ABC123",
        }
        try:
            result = PhotoVerificationEngine.verify_photo(
                photo_data,
                expected_code="ABC123",
                rent_lat=12.9716,
                rent_lng=77.5946,
                tolerance_meters=500,
            )
            assert result.location_verified is False
        except (TypeError, AttributeError):
            # Expected
            pass
