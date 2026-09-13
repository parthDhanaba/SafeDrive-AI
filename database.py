"""
SafeDrive-AI SQLite Database Subsystem
Handles driver profiles, vehicle registration, safety telemetry event logging,
and emergency SOS alert records with non-destructive migrations.
"""
import sqlite3
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from config import DATABASE_PATH
from logger import logger


def get_connection() -> sqlite3.Connection:
    """Creates a database connection with foreign key enforcement and row factory."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _migrate_table_columns(connection: sqlite3.Connection, table_name: str, new_columns: Dict[str, str]):
    """Safely adds missing columns to an existing SQLite table."""
    cursor = connection.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    existing_cols = {row["name"] for row in cursor.fetchall()}

    for col_name, col_type in new_columns.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                logger.info(f"Database migration: Added column '{col_name}' ({col_type}) to table '{table_name}'.")
            except Exception as e:
                logger.warning(f"Failed to add column '{col_name}' to table '{table_name}': {e}")
    connection.commit()


def initialize_database():
    """Initializes tables and performs non-destructive schema migrations."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()

        # Drivers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Vehicles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_number TEXT NOT NULL UNIQUE,
                vehicle_type TEXT,
                owner_name TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Safety events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                vehicle_id INTEGER,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                ear_value REAL,
                mar_value REAL,
                yawn_count INTEGER DEFAULT 0,
                closed_frames INTEGER DEFAULT 0,
                response_status TEXT,
                latitude REAL,
                longitude REAL,
                location_accuracy REAL,
                alarm_triggered INTEGER DEFAULT 0,
                hazard_activated INTEGER DEFAULT 0,
                sos_sent INTEGER DEFAULT 0,
                photo_path TEXT,
                notification_status TEXT DEFAULT 'NONE',
                timestamp TEXT NOT NULL,
                FOREIGN KEY (driver_id) REFERENCES drivers(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );
        """)

        # Emergency alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                recipient_type TEXT,
                recipient_name TEXT,
                recipient_phone TEXT,
                message TEXT,
                latitude REAL,
                longitude REAL,
                location_accuracy REAL,
                photo_path TEXT,
                sent_at TEXT NOT NULL,
                delivery_status TEXT,
                whatsapp_attempted INTEGER DEFAULT 0,
                whatsapp_succeeded INTEGER DEFAULT 0,
                location_available INTEGER DEFAULT 0,
                photo_captured INTEGER DEFAULT 0,
                channel TEXT DEFAULT 'SMS',
                FOREIGN KEY (event_id) REFERENCES safety_events(id)
            );
        """)
        conn.commit()

        # Perform safe schema migrations for existing databases
        _migrate_table_columns(conn, "safety_events", {
            "location_accuracy": "REAL",
            "photo_path": "TEXT",
            "notification_status": "TEXT DEFAULT 'NONE'"
        })
        _migrate_table_columns(conn, "emergency_alerts", {
            "location_accuracy": "REAL",
            "photo_path": "TEXT",
            "whatsapp_attempted": "INTEGER DEFAULT 0",
            "whatsapp_succeeded": "INTEGER DEFAULT 0",
            "location_available": "INTEGER DEFAULT 0",
            "photo_captured": "INTEGER DEFAULT 0",
            "channel": "TEXT DEFAULT 'SMS'"
        })

    logger.info("Database schema initialized and verified successfully.")


def add_driver(name: str, phone: str = "", emergency_contact_name: str = "", emergency_contact_phone: str = "") -> int:
    """Inserts a new driver record and returns its ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO drivers (
                name,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            name.strip(),
            phone.strip(),
            emergency_contact_name.strip(),
            emergency_contact_phone.strip(),
            datetime.now().isoformat()
        ))
        conn.commit()
        return cursor.lastrowid


def add_vehicle(vehicle_number: str, vehicle_type: str = "Car", owner_name: str = "") -> int:
    """Inserts or retrieves a vehicle record and returns its ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO vehicles (
                vehicle_number,
                vehicle_type,
                owner_name,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            vehicle_number.strip().upper(),
            vehicle_type.strip(),
            owner_name.strip(),
            datetime.now().isoformat()
        ))
        conn.commit()

        cursor.execute("SELECT id FROM vehicles WHERE vehicle_number = ?", (vehicle_number.strip().upper(),))
        row = cursor.fetchone()
        return row["id"] if row else 1


def get_driver(driver_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Retrieves driver record by ID."""
    if not driver_id:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_vehicle(vehicle_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Retrieves vehicle record by ID."""
    if not vehicle_id:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_default_profile() -> Tuple[Optional[int], Optional[int]]:
    """Returns (driver_id, vehicle_id) for the latest active profiles."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM drivers ORDER BY id DESC LIMIT 1;")
        driver = cursor.fetchone()

        cursor.execute("SELECT id FROM vehicles ORDER BY id DESC LIMIT 1;")
        vehicle = cursor.fetchone()

        driver_id = driver["id"] if driver else None
        vehicle_id = vehicle["id"] if vehicle else None
        return driver_id, vehicle_id


def save_safety_event(
    driver_id: Optional[int],
    vehicle_id: Optional[int],
    event_type: str,
    severity: str,
    ear_value: Optional[float],
    mar_value: Optional[float],
    yawn_count: int = 0,
    closed_frames: int = 0,
    response_status: str = "DETECTED",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_accuracy: Optional[float] = None,
    alarm_triggered: bool = False,
    hazard_activated: bool = False,
    sos_sent: bool = False,
    photo_path: Optional[str] = None,
    notification_status: str = "NONE"
) -> int:
    """Records a driver attentiveness or safety event into SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO safety_events (
                driver_id,
                vehicle_id,
                event_type,
                severity,
                ear_value,
                mar_value,
                yawn_count,
                closed_frames,
                response_status,
                latitude,
                longitude,
                location_accuracy,
                alarm_triggered,
                hazard_activated,
                sos_sent,
                photo_path,
                notification_status,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            driver_id,
            vehicle_id,
            event_type,
            severity,
            round(ear_value, 4) if ear_value is not None else None,
            round(mar_value, 4) if mar_value is not None else None,
            yawn_count,
            closed_frames,
            response_status,
            latitude,
            longitude,
            location_accuracy,
            int(alarm_triggered),
            int(hazard_activated),
            int(sos_sent),
            str(photo_path) if photo_path else None,
            notification_status,
            datetime.now().isoformat()
        ))
        conn.commit()
        return cursor.lastrowid


def save_emergency_alert(
    event_id: Optional[int],
    recipient_type: str,
    recipient_name: str,
    recipient_phone: str,
    message: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_accuracy: Optional[float] = None,
    photo_path: Optional[str] = None,
    delivery_status: str = "PENDING",
    whatsapp_attempted: int = 0,
    whatsapp_succeeded: int = 0,
    location_available: int = 0,
    photo_captured: int = 0,
    channel: str = "SMS"
) -> int:
    """Logs an outgoing or simulated emergency alert dispatch."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emergency_alerts (
                event_id,
                recipient_type,
                recipient_name,
                recipient_phone,
                message,
                latitude,
                longitude,
                location_accuracy,
                photo_path,
                sent_at,
                delivery_status,
                whatsapp_attempted,
                whatsapp_succeeded,
                location_available,
                photo_captured,
                channel
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            recipient_type,
            recipient_name,
            recipient_phone,
            message,
            latitude,
            longitude,
            location_accuracy,
            str(photo_path) if photo_path else None,
            datetime.now().isoformat(),
            delivery_status,
            int(whatsapp_attempted),
            int(whatsapp_succeeded),
            int(location_available),
            int(photo_captured),
            channel
        ))
        conn.commit()
        return cursor.lastrowid


def get_emergency_alerts_for_event(event_id: int) -> List[Dict[str, Any]]:
    """Retrieves all alert dispatches associated with a safety event."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_alerts WHERE event_id = ? ORDER BY id ASC;", (event_id,))
        return [dict(r) for r in cursor.fetchall()]


def get_event_statistics() -> Dict[str, Any]:
    """Computes summary statistics for UI dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS c FROM safety_events WHERE event_type LIKE '%YAWN%';")
        total_yawns = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM safety_events WHERE event_type = 'DROWSINESS';")
        drowsy_events = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM safety_events WHERE event_type = 'EMERGENCY';")
        emergency_events = cursor.fetchone()["c"]

        cursor.execute("SELECT timestamp FROM safety_events WHERE event_type = 'EMERGENCY' ORDER BY id DESC LIMIT 1;")
        last_emerg_row = cursor.fetchone()
        last_emergency = last_emerg_row["timestamp"] if last_emerg_row else "None"

        return {
            "total_yawns": total_yawns,
            "drowsiness_events": drowsy_events,
            "emergency_events": emergency_events,
            "last_emergency": last_emergency
        }


def get_recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches recent safety events for history review."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, event_type, severity, ear_value, mar_value, yawn_count,
                   closed_frames, response_status, alarm_triggered, hazard_activated,
                   sos_sent, notification_status, timestamp
            FROM safety_events
            ORDER BY id DESC
            LIMIT ?;
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]