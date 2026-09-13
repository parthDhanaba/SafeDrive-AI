"""
SafeDrive-AI Windows Device Location Subsystem
Fetches actual device coordinates via Windows Location Services (GeoCoordinateWatcher).
Safely handles permission issues, hardware timeouts, and coordinates caching.
Does NOT use IP geolocation and never fabricates coordinates.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import subprocess
import json
import threading
from logger import logger

# Script to query Windows native GeoCoordinateWatcher
_POWERSHELL_GEO_SCRIPT = """
Add-Type -AssemblyName System.Device
$watcher = New-Object System.Device.Location.GeoCoordinateWatcher
$watcher.Start()
for ($i = 0; $i -lt 30; $i++) {
    if ($watcher.Status -eq [System.Device.Location.GeoPositionStatus]::Ready) {
        break
    }
    Start-Sleep -Milliseconds 100
}
$loc = $watcher.Position.Location
if ($loc.IsUnknown) {
    Write-Output "UNAVAILABLE"
} else {
    $out = [PSCustomObject]@{
        Latitude = $loc.Latitude
        Longitude = $loc.Longitude
        HorizontalAccuracy = $loc.HorizontalAccuracy
    }
    $out | ConvertTo-Json -Compress
}
$watcher.Stop()
"""


@dataclass
class Location:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    is_available: bool = False
    status_text: str = "Unavailable"
    timestamp: Optional[str] = None

    @property
    def maps_url(self) -> str:
        """Returns Google Maps URL if valid coordinates exist, else 'Unavailable'."""
        if self.is_available and self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return "Unavailable"

    def summary(self) -> str:
        """Returns concise single-line description."""
        if self.is_available and self.latitude is not None and self.longitude is not None:
            acc_str = f" ±{self.accuracy:.0f}m" if self.accuracy is not None else ""
            return f"Lat {self.latitude:.5f}, Lon {self.longitude:.5f}{acc_str}"
        return self.status_text


class LocationProvider:
    """Manages Windows device location resolution with background prefetching and caching."""

    def __init__(self):
        self._cached_location = Location(is_available=False, status_text="Acquiring...")
        self._lock = threading.Lock()
        self._is_fetching = False

    def prefetch_location(self):
        """Asynchronously warms up location in the background so emergency lookups are instantaneous."""
        if self._is_fetching:
            return

        def _fetch_worker():
            self._is_fetching = True
            loc = self.get_device_location(timeout=6.0)
            with self._lock:
                self._cached_location = loc
            self._is_fetching = False

        thread = threading.Thread(target=_fetch_worker, daemon=True)
        thread.start()

    def get_cached_location(self) -> Location:
        """Instantly returns the latest cached location."""
        with self._lock:
            return self._cached_location

    def get_device_location(self, timeout: float = 4.0) -> Location:
        """
        Queries Windows GeoCoordinateWatcher for device location.
        Falls back safely to 'Unavailable' on permission denial or timeout.
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _POWERSHELL_GEO_SCRIPT],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = res.stdout.strip()

            if not stdout or "UNAVAILABLE" in stdout or res.returncode != 0:
                logger.info("Windows Location Services reported position unknown or unavailable.")
                return Location(
                    is_available=False,
                    status_text="Unavailable",
                    timestamp=datetime.now().isoformat()
                )

            data = json.loads(stdout)
            lat = float(data.get("Latitude", 0.0))
            lon = float(data.get("Longitude", 0.0))
            acc = float(data.get("HorizontalAccuracy", 0.0)) if "HorizontalAccuracy" in data else None

            loc = Location(
                latitude=lat,
                longitude=lon,
                accuracy=acc,
                is_available=True,
                status_text="Available",
                timestamp=datetime.now().isoformat()
            )
            with self._lock:
                self._cached_location = loc
            logger.info(f"Retrieved emergency location: {loc.summary()}")
            return loc

        except subprocess.TimeoutExpired:
            logger.warning("Windows Location acquisition timed out.")
            with self._lock:
                if self._cached_location.is_available:
                    return self._cached_location
            return Location(is_available=False, status_text="Timeout", timestamp=datetime.now().isoformat())
        except Exception as e:
            logger.warning(f"Error accessing Windows Location Services: {e}")
            with self._lock:
                if self._cached_location.is_available:
                    return self._cached_location
            return Location(is_available=False, status_text="Unavailable", timestamp=datetime.now().isoformat())


# Global singleton instance
location_provider = LocationProvider()


def get_emergency_location() -> Location:
    """Helper function to fetch current device location or last cached valid fix."""
    cached = location_provider.get_cached_location()
    if cached.is_available:
        return cached
    return location_provider.get_device_location()