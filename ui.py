"""
SafeDrive-AI Premium Desktop Dashboard UI
Modern dark-mode glassmorphic dashboard built with CustomTkinter & PIL.
Displays live camera feed, real-time facial telemetry, emergency countdowns,
Windows GPS coordinates, SOS status, statistics, and event history.
"""
import sys
import os
import time
import webbrowser
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageTk

try:
    import customtkinter as ctk
except ImportError:
    import tkinter as ctk  # Fallback

from config import (
    APP_NAME,
    APP_VERSION,
    EAR_THRESHOLD,
    MAR_THRESHOLD,
    YAWN_LIMIT,
    RESPONSE_TIMEOUT_SECONDS,
    DATABASE_PATH
)
from logger import logger
from utils import mask_phone_number, get_display_timestamp
from database import get_driver, get_vehicle, get_event_statistics, get_recent_events


# Theme Color Palette (Curated Obsidian / Dark Slate)
BG_MAIN = "#0B0F19"
CARD_BG = "#131B2E"
CARD_BORDER = "#1E293B"
ACCENT_BLUE = "#38BDF8"
ACCENT_GREEN = "#10B981"
ACCENT_AMBER = "#F59E0B"
ACCENT_RED = "#EF4444"
ACCENT_CRIMSON = "#991B1B"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_DIM = "#64748B"


class EventHistoryDialog(ctk.CTkToplevel):
    """Modal window displaying recent safety telemetry and emergency events."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("SafeDrive AI - Event History & Audit Log")
        self.geometry("820x520")
        self.configure(fg_color=BG_MAIN)
        self.transient(parent)
        self.grab_set()

        title_lbl = ctk.CTkLabel(
            self,
            text="Recent Safety & Emergency Events",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_MAIN
        )
        title_lbl.pack(padx=20, pady=(20, 10), anchor="w")

        # Scrollable Frame
        scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=CARD_BG,
            border_color=CARD_BORDER,
            border_width=1,
            corner_radius=8
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Headers
        headers = ["ID", "Timestamp", "Event Type", "Severity", "EAR", "MAR", "Yawns", "Status", "SOS"]
        hdr_frame = ctk.CTkFrame(scroll_frame, fg_color=CARD_BORDER, corner_radius=4)
        hdr_frame.pack(fill="x", pady=2, padx=2)
        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                hdr_frame,
                text=h,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=TEXT_MUTED,
                width=80
            )
            lbl.grid(row=0, column=i, padx=4, pady=6)

        try:
            events = get_recent_events(limit=30)
            if not events:
                empty_lbl = ctk.CTkLabel(
                    scroll_frame,
                    text="No safety events logged yet.",
                    font=ctk.CTkFont(family="Segoe UI", size=13),
                    text_color=TEXT_DIM
                )
                empty_lbl.pack(pady=40)
            else:
                for ev in events:
                    row_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=1)

                    sev = ev.get("severity", "NORMAL")
                    sev_color = ACCENT_RED if sev == "CRITICAL" else (ACCENT_AMBER if sev == "HIGH" else TEXT_MAIN)

                    ts_short = ev.get("timestamp", "")[:19].replace("T", " ")
                    cols = [
                        str(ev.get("id", "")),
                        ts_short,
                        str(ev.get("event_type", "")),
                        str(sev),
                        f"{ev.get('ear_value') or 0:.2f}",
                        f"{ev.get('mar_value') or 0:.2f}",
                        str(ev.get("yawn_count", 0)),
                        str(ev.get("response_status", "DETECTED")),
                        "YES" if ev.get("sos_sent") else "NO"
                    ]

                    for col_idx, val in enumerate(cols):
                        txt_col = sev_color if col_idx == 3 else TEXT_MAIN
                        c_lbl = ctk.CTkLabel(
                            row_frame,
                            text=val,
                            font=ctk.CTkFont(family="Segoe UI", size=11),
                            text_color=txt_col,
                            width=80
                        )
                        c_lbl.grid(row=0, column=col_idx, padx=4, pady=4)
        except Exception as e:
            err_lbl = ctk.CTkLabel(scroll_frame, text=f"Error reading history: {e}", text_color=ACCENT_RED)
            err_lbl.pack(pady=20)


class SafeDriveDashboard(ctk.CTk):
    """Primary SafeDrive-AI Desktop User Interface."""

    def __init__(
        self,
        on_reset_callback: Optional[Callable] = None,
        on_quit_callback: Optional[Callable] = None,
        driver_id: Optional[int] = None,
        vehicle_id: Optional[int] = None
    ):
        super().__init__()

        self.on_reset_callback = on_reset_callback
        self.on_quit_callback = on_quit_callback
        self.driver_id = driver_id
        self.vehicle_id = vehicle_id

        # Profile Data
        self.driver_data = get_driver(driver_id) or {"name": "Primary Driver", "phone": "N/A"}
        self.vehicle_data = get_vehicle(vehicle_id) or {"vehicle_number": "MH-08-AB-1234", "vehicle_type": "Car"}

        # Responsive Window Setup
        self.title(f"{APP_NAME} - Advanced Driver Safety Dashboard v{APP_VERSION}")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1280, max(1040, int(screen_w * 0.88)))
        win_h = min(820, max(680, int(screen_h * 0.84)))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(980, 640)
        self.configure(fg_color=BG_MAIN)

        # State tracking
        self.is_monitoring = True
        self.last_maps_url = ""
        self.photo_image = None

        # Build Layout
        self._build_header()
        self._build_body()
        self._build_controls()
        self._bind_keys()

    def _build_header(self):
        """Builds top bar with title, driver info, and system status badge."""
        self.header_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        self.header_frame.pack(fill="x", padx=16, pady=(12, 8))

        # App Logo & Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)

        app_title = ctk.CTkLabel(
            title_box,
            text=f"🛡️  {APP_NAME.upper()}",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=ACCENT_BLUE
        )
        app_title.pack(side="left")

        app_sub = ctk.CTkLabel(
            title_box,
            text=f" v{APP_VERSION} | AI Driver Safety System",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_DIM
        )
        app_sub.pack(side="left", padx=(6, 0), pady=(4, 0))

        # Right Controls: Driver, Vehicle, System Status
        right_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=10)

        d_name = self.driver_data.get("name", "Driver")
        v_num = self.vehicle_data.get("vehicle_number", "Vehicle")

        profile_lbl = ctk.CTkLabel(
            right_box,
            text=f"👤 Driver: {d_name}   |   🚗 Vehicle: {v_num}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_MUTED
        )
        profile_lbl.pack(side="left", padx=(0, 20))

        self.status_pill = ctk.CTkLabel(
            right_box,
            text="● MONITORING ACTIVE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#000000",
            fg_color=ACCENT_GREEN,
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.status_pill.pack(side="left")

    def _build_body(self):
        """Constructs split layout: Video feed (left) and telemetry sidebar (right)."""
        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, padx=16, pady=4)

        # -------------------------------------------------------------
        # Left Panel: Live Camera & Vision
        # -------------------------------------------------------------
        self.left_panel = ctk.CTkFrame(self.body_frame, fg_color=CARD_BG, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Camera Header Bar
        cam_hdr = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        cam_hdr.pack(fill="x", padx=14, pady=(10, 6))

        cam_title = ctk.CTkLabel(
            cam_hdr,
            text="LIVE VISION & FACIAL TELEMETRY",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=TEXT_MAIN
        )
        cam_title.pack(side="left")

        self.fps_badge = ctk.CTkLabel(
            cam_hdr,
            text="FPS: --",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_BLUE
        )
        self.fps_badge.pack(side="right")

        # Video Frame Canvas / Label
        self.video_label = ctk.CTkLabel(self.left_panel, text="Initializing Camera Stream...", fg_color="#050811", corner_radius=8)
        self.video_label.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Prominent Emergency / Warning Notification Banner (Under Camera)
        self.alert_banner = ctk.CTkFrame(self.left_panel, fg_color="#0F172A", corner_radius=8, height=48)
        self.alert_banner.pack(fill="x", padx=12, pady=(0, 12))

        self.alert_banner_text = ctk.CTkLabel(
            self.alert_banner,
            text="Status: Driver Attentive - Normal Operations",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=ACCENT_GREEN
        )
        self.alert_banner_text.pack(pady=10)

        # -------------------------------------------------------------
        # Right Panel: Telemetry, Emergency, Location, and Stats
        # -------------------------------------------------------------
        self.right_panel = ctk.CTkScrollableFrame(
            self.body_frame,
            fg_color=CARD_BG,
            corner_radius=10,
            border_color=CARD_BORDER,
            border_width=1,
            width=420
        )
        self.right_panel.pack(side="right", fill="both", padx=(8, 0))

        self._build_safety_panel()
        self._build_emergency_panel()
        self._build_location_panel()
        self._build_statistics_panel()

    def _build_safety_panel(self):
        """Driver safety metrics: EAR, MAR, Eye State, Yawn counts."""
        frame = ctk.CTkFrame(self.right_panel, fg_color="#18233C", corner_radius=8)
        frame.pack(fill="x", padx=10, pady=(10, 6))

        hdr = ctk.CTkLabel(
            frame,
            text="DRIVER ATTENTIVENESS METRICS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_BLUE
        )
        hdr.pack(anchor="w", padx=12, pady=(8, 6))

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 10))

        # EAR Metric
        self.val_ear = self._create_metric_box(grid, 0, 0, "EAR (Eyes)", "0.00", f"Thresh: {EAR_THRESHOLD}")
        # MAR Metric
        self.val_mar = self._create_metric_box(grid, 0, 1, "MAR (Mouth)", "0.00", f"Thresh: {MAR_THRESHOLD}")
        # Closed Frames
        self.val_closed = self._create_metric_box(grid, 1, 0, "Eye State", "OPEN", "Closed: 0 / 45")
        # Yawns
        self.val_yawns = self._create_metric_box(grid, 1, 1, "Yawn Count", "0 / 3", "Danger: >= 3")

    def _create_metric_box(self, parent, row, col, label, initial_val, subtext=""):
        box = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=6, border_color=CARD_BORDER, border_width=1)
        box.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(box, text=label, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=8, pady=(6, 0))
        val_lbl = ctk.CTkLabel(box, text=initial_val, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=TEXT_MAIN)
        val_lbl.pack(anchor="w", padx=8, pady=(2, 0))
        sub_lbl = ctk.CTkLabel(box, text=subtext, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_DIM)
        sub_lbl.pack(anchor="w", padx=8, pady=(0, 6))
        return val_lbl

    def _build_emergency_panel(self):
        """Emergency and SOS status indicators."""
        self.emerg_frame = ctk.CTkFrame(self.right_panel, fg_color="#18233C", corner_radius=8)
        self.emerg_frame.pack(fill="x", padx=10, pady=6)

        hdr = ctk.CTkLabel(
            self.emerg_frame,
            text="EMERGENCY & SOS STATUS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_AMBER
        )
        hdr.pack(anchor="w", padx=12, pady=(8, 4))

        # Status Rows
        self.lbl_countdown = self._create_status_row(self.emerg_frame, "Countdown Timer", "INACTIVE", TEXT_MUTED)
        self.lbl_alarm_state = self._create_status_row(self.emerg_frame, "Audible Alarm", "STANDBY", TEXT_MUTED)
        self.lbl_hazard_state = self._create_status_row(self.emerg_frame, "Hazard Lights", "OFF", TEXT_MUTED)
        self.lbl_photo_state = self._create_status_row(self.emerg_frame, "Snapshot", "Ready", TEXT_MUTED)
        self.lbl_sms_state = self._create_status_row(self.emerg_frame, "Notification Provider", "Mock SMS (Simulated)", ACCENT_BLUE)

    def _create_status_row(self, parent, label, default_value, color=TEXT_MAIN):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)

        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED).pack(side="left")
        val_lbl = ctk.CTkLabel(row, text=default_value, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=color)
        val_lbl.pack(side="right")
        return val_lbl

    def _build_location_panel(self):
        """Windows Device Location card."""
        frame = ctk.CTkFrame(self.right_panel, fg_color="#18233C", corner_radius=8)
        frame.pack(fill="x", padx=10, pady=6)

        hdr = ctk.CTkLabel(
            frame,
            text="EMERGENCY LOCATION (DEVICE GPS)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_BLUE
        )
        hdr.pack(anchor="w", padx=12, pady=(8, 4))

        self.lbl_gps_coords = self._create_status_row(frame, "Coordinates", "Acquiring...", TEXT_MUTED)
        self.lbl_gps_accuracy = self._create_status_row(frame, "Accuracy", "--", TEXT_DIM)

        # Maps button
        self.btn_maps = ctk.CTkButton(
            frame,
            text="Open in Google Maps",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._open_maps_url,
            height=28
        )
        self.btn_maps.pack(fill="x", padx=12, pady=(6, 10))

    def _build_statistics_panel(self):
        """Summary session statistics."""
        frame = ctk.CTkFrame(self.right_panel, fg_color="#18233C", corner_radius=8)
        frame.pack(fill="x", padx=10, pady=6)

        hdr = ctk.CTkLabel(
            frame,
            text="SYSTEM STATISTICS & AUDIT",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_MUTED
        )
        hdr.pack(anchor="w", padx=12, pady=(8, 4))

        stats = get_event_statistics()
        self.lbl_stat_yawns = self._create_status_row(frame, "Total Yawn Events", str(stats.get("total_yawns", 0)))
        self.lbl_stat_drowsy = self._create_status_row(frame, "Drowsiness Triggers", str(stats.get("drowsiness_events", 0)))
        self.lbl_stat_emerg = self._create_status_row(frame, "Emergency SOS Events", str(stats.get("emergency_events", 0)))
        last_em = stats.get("last_emergency", "None")
        if last_em and last_em != "None":
            last_em = last_em[:19].replace("T", " ")
        self.lbl_stat_last = self._create_status_row(frame, "Last Emergency", str(last_em), TEXT_DIM)

    def _build_controls(self):
        """Action buttons at the bottom of the dashboard."""
        self.ctrl_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        self.ctrl_frame.pack(fill="x", padx=16, pady=(6, 14))

        # Reset Button (R)
        self.btn_reset = ctk.CTkButton(
            self.ctrl_frame,
            text="RESET ALARM & DETECTION (R)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=38,
            command=self._on_reset_pressed
        )
        self.btn_reset.pack(side="left", padx=(14, 8), pady=10)

        # View History Button
        self.btn_history = ctk.CTkButton(
            self.ctrl_frame,
            text="📋 View Event History",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=38,
            command=self._open_history_dialog
        )
        self.btn_history.pack(side="left", padx=8, pady=10)

        # Quit Button (Q)
        self.btn_quit = ctk.CTkButton(
            self.ctrl_frame,
            text="QUIT (Q)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#450A0A",
            hover_color="#7F1D1D",
            height=38,
            command=self._on_quit_pressed
        )
        self.btn_quit.pack(side="right", padx=(8, 14), pady=10)

    def _bind_keys(self):
        """Binds R and Q hotkeys."""
        self.bind("<r>", lambda event: self._on_reset_pressed())
        self.bind("<R>", lambda event: self._on_reset_pressed())
        self.bind("<q>", lambda event: self._on_quit_pressed())
        self.bind("<Q>", lambda event: self._on_quit_pressed())
        self.protocol("WM_DELETE_WINDOW", self._on_quit_pressed)

    def _on_reset_pressed(self):
        """Triggers emergency and detection reset."""
        if self.on_reset_callback:
            self.on_reset_callback()

    def _on_quit_pressed(self):
        """Cleanly terminates application."""
        self.is_monitoring = False
        if self.on_quit_callback:
            self.on_quit_callback()
        self.destroy()

    def _open_maps_url(self):
        """Opens current GPS location in user's default browser."""
        if self.last_maps_url and "maps" in self.last_maps_url:
            webbrowser.open(self.last_maps_url)

    def _open_history_dialog(self):
        """Displays recent event audit log dialog."""
        EventHistoryDialog(self)

    def update_frame(self, frame):
        """Updates the video feed canvas smoothly with a new OpenCV frame, dynamically fitted to available bounds."""
        if frame is None or not self.winfo_exists():
            return

        try:
            # Measure actual container space in left panel
            lbl_w = self.video_label.winfo_width()
            lbl_h = self.video_label.winfo_height()

            # Fallback if window not yet rendered
            if lbl_w < 100 or lbl_h < 100:
                lbl_w = 640
                lbl_h = 420

            h, w, _ = frame.shape
            scale = min((lbl_w - 8) / max(w, 1), (lbl_h - 8) / max(h, 1))
            target_w = max(int(w * scale), 10)
            target_h = max(int(h * scale), 10)

            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            self.photo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))

            self.video_label.configure(image=self.photo_image, text="")
        except Exception as e:
            logger.error(f"Error rendering video frame in UI: {e}")

    def update_telemetry(
        self,
        fps: float,
        eye_data: Dict[str, Any],
        emerg_status: Dict[str, Any],
        location_obj
    ):
        """Updates all dashboard labels, metric cards, and emergency banners."""
        if not self.winfo_exists():
            return

        # FPS
        self.fps_badge.configure(text=f"FPS: {fps:.1f}")

        # Metrics
        ear = eye_data.get("ear", 0.0)
        mar = eye_data.get("mar", 0.0)
        state = eye_data.get("state", "OPEN")
        closed = eye_data.get("closed_frames", 0)
        yawns = eye_data.get("yawns", 0)
        drowsy = eye_data.get("drowsy", False)

        self.val_ear.configure(text=f"{ear:.2f}")
        self.val_mar.configure(text=f"{mar:.2f}")
        self.val_closed.configure(text=f"{state} ({closed}f)")
        self.val_yawns.configure(text=f"{yawns} / {YAWN_LIMIT}")

        # Location
        if location_obj and location_obj.is_available:
            self.lbl_gps_coords.configure(text=f"{location_obj.latitude:.5f}, {location_obj.longitude:.5f}", text_color=ACCENT_GREEN)
            acc_str = f"±{location_obj.accuracy:.0f}m" if location_obj.accuracy else "GPS Fix"
            self.lbl_gps_accuracy.configure(text=acc_str, text_color=TEXT_MAIN)
            self.last_maps_url = location_obj.maps_url
            self.btn_maps.configure(state="normal", text="Open in Google Maps")
        else:
            self.lbl_gps_coords.configure(text="Unavailable", text_color=TEXT_MUTED)
            self.lbl_gps_accuracy.configure(text="No GPS permission/signal", text_color=TEXT_DIM)
            self.btn_maps.configure(state="disabled", text="Location Unavailable")

        # Emergency & Warning States
        is_emergency = emerg_status.get("is_emergency", False)
        countdown_active = emerg_status.get("countdown_active", False)
        rem_time = emerg_status.get("remaining_time", RESPONSE_TIMEOUT_SECONDS)
        danger_reason = emerg_status.get("danger_reason", "")
        alarm_on = emerg_status.get("alarm_active", False)
        hazard_on = emerg_status.get("hazard_lights", False)
        notif_status = emerg_status.get("notification_status", "IDLE")
        provider = emerg_status.get("provider_name", "Mock SMS")

        self.lbl_alarm_state.configure(
            text="LOUD ALARM ON" if alarm_on else "STANDBY",
            text_color=ACCENT_RED if alarm_on else TEXT_MUTED
        )
        self.lbl_hazard_state.configure(
            text="FLASHING (ON)" if hazard_on else "OFF",
            text_color=ACCENT_AMBER if hazard_on else TEXT_MUTED
        )
        self.lbl_photo_state.configure(text=emerg_status.get("photo_status", "Ready"))
        self.lbl_sms_state.configure(
            text=f"{provider}: {notif_status}",
            text_color=ACCENT_GREEN if notif_status == "SIMULATED" or notif_status == "SENT" else (ACCENT_RED if notif_status == "FAILED" else TEXT_MUTED)
        )

        # State Coloring & Banners
        if is_emergency:
            self.status_pill.configure(text="● EMERGENCY ACTIVE", fg_color=ACCENT_RED, text_color="#FFFFFF")
            self.alert_banner.configure(fg_color="#450A0A")
            self.alert_banner_text.configure(
                text=f"🚨 EMERGENCY MODE ACTIVATED - SOS DISPATCHED ({notif_status}) - PRESS 'R' TO RESET",
                text_color="#FEF2F2"
            )
            self.lbl_countdown.configure(text="TIMED OUT (SOS SENT)", text_color=ACCENT_RED)
            self.btn_reset.configure(fg_color=ACCENT_RED, hover_color="#B91C1C")

        elif countdown_active:
            self.status_pill.configure(text="● DANGER WARNING", fg_color=ACCENT_AMBER, text_color="#000000")
            self.alert_banner.configure(fg_color="#3B1700")
            self.alert_banner_text.configure(
                text=f"⚠️ {danger_reason.upper()} | RESPOND IN {rem_time}s (PRESS 'R')",
                text_color=ACCENT_AMBER
            )
            self.lbl_countdown.configure(text=f"RESPOND IN: {rem_time}s", text_color=ACCENT_AMBER)
            self.btn_reset.configure(fg_color=ACCENT_AMBER, hover_color="#D97706")

        elif drowsy or yawns > 0:
            self.status_pill.configure(text="● ATTENTION REQUIRED", fg_color="#CA8A04", text_color="#000000")
            self.alert_banner.configure(fg_color="#1E293B")
            self.alert_banner_text.configure(text=f"Notice: Yawn count: {yawns} / {YAWN_LIMIT}", text_color=ACCENT_AMBER)
            self.lbl_countdown.configure(text="INACTIVE", text_color=TEXT_MUTED)
            self.btn_reset.configure(fg_color="#1E3A8A", hover_color="#1D4ED8")

        else:
            self.status_pill.configure(text="● MONITORING ACTIVE", fg_color=ACCENT_GREEN, text_color="#000000")
            self.alert_banner.configure(fg_color="#0F172A")
            self.alert_banner_text.configure(text="Status: Driver Attentive - Safe Driving", text_color=ACCENT_GREEN)
            self.lbl_countdown.configure(text="INACTIVE", text_color=TEXT_MUTED)
            self.btn_reset.configure(fg_color="#1E3A8A", hover_color="#1D4ED8")
