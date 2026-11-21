"""Photo verification engine for geolocation and code detection."""
from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class PhotoVerificationResult:
    """Result of photo verification."""

    code_verified: bool
    location_verified: bool
    location_lat: Optional[float]
    location_lng: Optional[float]
    location_confidence: float
    distance_from_rent: Optional[float]
    issues: list[str]


class PhotoVerificationEngine:
    """Verify geo-tagged photos with written codes."""

    @staticmethod
    def extract_exif_location(photo_data: dict) -> tuple[Optional[float], Optional[float]]:
        """
        Extract geolocation from EXIF metadata.

        Args:
            photo_data: Dictionary containing photo metadata

        Returns:
            Tuple of (latitude, longitude) or (None, None)
        """
        try:
            lat = photo_data.get("location_lat")
            lng = photo_data.get("location_lng")
            if lat is not None and lng is not None:
                return float(lat), float(lng)
        except (ValueError, TypeError):
            pass
        return None, None

    @staticmethod
    def verify_code_presence(expected_code: str, detected_code: Optional[str]) -> bool:
        """
        Validate that photo contains written random code.

        Args:
            expected_code: The code that should be written
            detected_code: The code detected/submitted from the photo

        Returns:
            True if code matches or is readable, False otherwise
        """
        if not detected_code:
            return False

        # Simple string matching (placeholder for actual OCR logic)
        return detected_code.strip().upper() == expected_code.strip().upper()

    @staticmethod
    def calculate_distance(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """
        Calculate distance in meters between two coordinates (Haversine formula).

        Args:
            lat1, lng1: First coordinate
            lat2, lng2: Second coordinate

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def verify_photo(
        photo_data: dict,
        expected_code: str,
        rent_lat: Optional[float] = None,
        rent_lng: Optional[float] = None,
        tolerance_meters: int = 500,
    ) -> PhotoVerificationResult:
        """
        Verify a photo: code presence and geolocation.

        Args:
            photo_data: Dictionary with keys:
                - location_lat: EXIF latitude
                - location_lng: EXIF longitude
                - detected_code: The code written in the photo
                - timestamp: Photo timestamp
            expected_code: Random code that should be written in photo
            rent_lat: Rent address latitude
            rent_lng: Rent address longitude
            tolerance_meters: Maximum acceptable distance from rent address

        Returns:
            PhotoVerificationResult with verification details
        """
        issues = []
        result = PhotoVerificationResult(
            code_verified=False,
            location_verified=False,
            location_lat=None,
            location_lng=None,
            location_confidence=0.0,
            distance_from_rent=None,
            issues=issues,
        )

        # 1. Verify code
        detected_code = photo_data.get("detected_code")
        result.code_verified = PhotoVerificationEngine.verify_code_presence(
            expected_code, detected_code
        )
        if not result.code_verified:
            issues.append("Code not found or does not match expected value")

        # 2. Extract geolocation
        photo_lat, photo_lng = PhotoVerificationEngine.extract_exif_location(photo_data)
        if photo_lat is not None and photo_lng is not None:
            result.location_lat = photo_lat
            result.location_lng = photo_lng
            result.location_confidence = 0.95  # Placeholder: assuming good EXIF
        else:
            issues.append("No geolocation data in photo")
            return result

        # 3. Compare to rent address
        if rent_lat is not None and rent_lng is not None:
            distance = PhotoVerificationEngine.calculate_distance(
                photo_lat, photo_lng, rent_lat, rent_lng
            )
            result.distance_from_rent = distance

            if distance <= tolerance_meters:
                result.location_verified = True
            else:
                issues.append(
                    f"Photo location {distance:.0f}m from rent address (tolerance: {tolerance_meters}m)"
                )
        else:
            issues.append("Rent address coordinates not provided")

        return result
