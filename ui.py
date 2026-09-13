"""
SafeDrive-AI Modern Automotive Cockpit Dashboard UI
Realistic driver safety telemetry interface with dynamic visual gauges,
digital countdown timer, satellite GPS tracking, and glassmorphic styling.
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
from PIL import Image

try:
    import customtkinter as ctk
except ImportError:
    import tkinter as ctk

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

# Set global appearance mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Luxury Automotive Cockpit Palette (Obsidian / Titanium / Electric Cyan)
BG_MAIN = "#060911"
CARD_BG = "#0B1220"
CARD_SURFACE = "#111B30"
CARD_BORDER = "#1E2D4A"
CARD_BORDER_GLOW = "#06B6D4"

ACCENT_CYAN = "#06B6D4"
ACCENT_EMERALD = "#10B981"
ACCENT_AMBER = "#F59E0B"
ACCENT_RED = "#EF4444"
ACCENT_CRIMSON = "#991B1B"

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#94A3B8"
TEXT_DIM = "#64748B"


class EventHistoryDialog(ctk.CTkToplevel):
    """Cockpit Flight Telemetry & Event Audit Log Dialog."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("SafeDrive AI - Cockpit Event Audit Log")
        self.geometry("860x540")
        self.configure(fg_color=BG_MAIN)
        self.transient(parent)
        self.grab_set()

        hdr = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        hdr.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            hdr,
            text="📋  SAFETY INCIDENT & SOS AUDIT LOG",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left", padx=16, pady=12)

        scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=CARD_BG,
            border_color=CARD_BORDER,
            border_width=1,
            corner_radius=8
        )
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        headers = ["Event ID", "Timestamp", "Type", "Severity", "EAR", "MAR", "Yawns", "Action", "SOS Status"]
        hdr_frame = ctk.CTkFrame(scroll_frame, fg_color=CARD_SURFACE, corner_radius=6)
        hdr_frame.pack(fill="x", pady=4, padx=2)

        for i, h in enumerate(headers):
            ctk.CTkLabel(
                hdr_frame,
                text=h,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
                width=85
            ).grid(row=0, column=i, padx=4, pady=8)

        try:
            events = get_recent_events(limit=40)
            if not events:
                ctk.CTkLabel(
                    scroll_frame,
                    text="No safety events recorded in database yet.",
                    font=ctk.CTkFont(family="Segoe UI", size=13),
                    text_color=TEXT_DIM
                ).pack(pady=40)
            else:
                for ev in events:
                    row_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=2)

                    sev = ev.get("severity", "NORMAL")
                    sev_col = ACCENT_RED if sev == "CRITICAL" else (ACCENT_AMBER if sev == "HIGH" else ACCENT_EMERALD)
                    ts_short = ev.get("timestamp", "")[:19].replace("T", " ")

                    cols = [
                        f"#{ev.get('id', '')}",
                        ts_short,
                        str(ev.get("event_type", "")),
                        str(sev),
                        f"{ev.get('ear_value') or 0:.2f}",
                        f"{ev.get('mar_value') or 0:.2f}",
                        f"{ev.get('yawn_count', 0)}",
                        str(ev.get("response_status", "DETECTED")),
                        "SENT" if ev.get("sos_sent") else "NONE"
                    ]

                    for col_idx, val in enumerate(cols):
                        col_color = sev_col if col_idx == 3 else (ACCENT_CYAN if col_idx == 0 else TEXT_PRIMARY)
                        ctk.CTkLabel(
                            row_frame,
                            text=val,
                            font=ctk.CTkFont(family="Segoe UI", size=11),
                            text_color=col_color,
                            width=85
                        ).grid(row=0, column=col_idx, padx=4, pady=4)
        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"Error reading flight log: {e}", text_color=ACCENT_RED).pack(pady=20)


class SafeDriveDashboard(ctk.CTk):
    """Modern Automotive Driver Attentiveness Dashboard."""

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
        self.vehicle_data = get_vehicle(vehicle_id) or {"vehicle_number": "MH-08-SAFE-01", "vehicle_type": "SUV"}

        # Responsive Window Setup
        self.title(f"{APP_NAME} — Cockpit Safety Dashboard v{APP_VERSION}")
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1320, max(1040, int(screen_w * 0.90)))
        win_h = min(840, max(680, int(screen_h * 0.86)))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(980, 640)
        self.configure(fg_color=BG_MAIN)

        self.last_maps_url = ""
        self.photo_image = None
        self._hazard_flash_state = False

        # Build UI
        self._build_header()
        self._build_body()
        self._build_controls()
        self._bind_keys()
        self._start_clock()

    def _build_header(self):
        """Top infotainment bar with vehicle details, live clock, and status beacon."""
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=CARD_BG,
            corner_radius=12,
            border_color=CARD_BORDER,
            border_width=1
        )
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Brand Badge & System Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        ctk.CTkLabel(
            title_box,
            text="✦ SAFEDRIVE OS",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left")

        ctk.CTkLabel(
            title_box,
            text=" | PILOT ATTENTION GUARD",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_DIM
        ).pack(side="left", padx=(4, 0), pady=(3, 0))

        # Center: Driver & Vehicle Info Capsule
        d_name = self.driver_data.get("name", "Driver")
        v_num = self.vehicle_data.get("vehicle_number", "Vehicle")

        capsule = ctk.CTkFrame(self.header_frame, fg_color=CARD_SURFACE, corner_radius=20, border_color=CARD_BORDER, border_width=1)
        capsule.pack(side="left", expand=True, padx=10, pady=6)

        ctk.CTkLabel(
            capsule,
            text=f"👤 {d_name}    •    🚗 {v_num}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left", padx=(14, 10), pady=6)

        self.clock_lbl = ctk.CTkLabel(
            capsule,
            text="--:--:--",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_CYAN
        )
        self.clock_lbl.pack(side="left", padx=(0, 14), pady=6)

        # Right: System Health Pill Badge
        right_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=8)

        self.status_pill = ctk.CTkLabel(
            right_box,
            text="● AUTOPILOT GUARD: NOMINAL",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#000000",
            fg_color=ACCENT_EMERALD,
            corner_radius=14,
            padx=14,
            pady=5
        )
        self.status_pill.pack(side="right")

    def _start_clock(self):
        """Updates clock label each second."""
        if self.winfo_exists():
            now_str = datetime.now().strftime("%H:%M:%S")
            self.clock_lbl.configure(text=now_str)
            self.after(1000, self._start_clock)

    def _build_body(self):
        """Builds camera HUD (left) and telemetry console (right)."""
        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, padx=16, pady=4)

        # -------------------------------------------------------------
        # Left Panel: Camera Stream with Cockpit HUD Border
        # -------------------------------------------------------------
        self.left_panel = ctk.CTkFrame(
            self.body_frame,
            fg_color=CARD_BG,
            corner_radius=12,
            border_color=CARD_BORDER,
            border_width=1
        )
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Top Banner over video
        cam_hdr = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        cam_hdr.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            cam_hdr,
            text="AI CABIN OPTICAL TELEMETRY",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        self.fps_badge = ctk.CTkLabel(
            cam_hdr,
            text="FPS: 30.0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_CYAN,
            fg_color=CARD_SURFACE,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.fps_badge.pack(side="right")

        # Video Frame Container
        self.video_container = ctk.CTkFrame(self.left_panel, fg_color="#020408", corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.video_label = ctk.CTkLabel(
            self.video_container,
            text="Initializing High-FPS Vision Stream...",
            text_color=TEXT_DIM
        )
        self.video_label.pack(fill="both", expand=True)

        # Alert Banner (Under Camera)
        self.alert_banner = ctk.CTkFrame(self.left_panel, fg_color=CARD_SURFACE, corner_radius=8, height=44)
        self.alert_banner.pack(fill="x", padx=12, pady=(0, 10))

        self.alert_banner_text = ctk.CTkLabel(
            self.alert_banner,
            text="[ SAFE ] Driver Attentive — All Telemetry Nominal",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=ACCENT_EMERALD
        )
        self.alert_banner_text.pack(pady=8)

        # -------------------------------------------------------------
        # Right Panel: Cockpit Telemetry Sidebar
        # -------------------------------------------------------------
        self.right_panel = ctk.CTkScrollableFrame(
            self.body_frame,
            fg_color=CARD_BG,
            corner_radius=12,
            border_color=CARD_BORDER,
            border_width=1,
            width=390
        )
        self.right_panel.pack(side="right", fill="both", expand=False, padx=(8, 0))

        self._build_safety_gauges()
        self._build_emergency_console()
        self._build_location_card()
        self._build_flight_stats()

    def _build_safety_gauges(self):
        """Realistic dynamic visual gauges for EAR, MAR, and Yawn counts."""
        frame = ctk.CTkFrame(self.right_panel, fg_color=CARD_SURFACE, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        frame.pack(fill="x", padx=8, pady=(8, 6))

        hdr_row = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            hdr_row,
            text="DRIVER ATTENTION GAUGES",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left")

        # 1. EAR Gauge Box
        ear_box = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        ear_box.pack(fill="x", padx=10, pady=4)

        ear_hdr = ctk.CTkFrame(ear_box, fg_color="transparent")
        ear_hdr.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(ear_hdr, text="EYE ASPECT RATIO (EAR)", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=TEXT_SECONDARY).pack(side="left")
        self.lbl_ear_val = ctk.CTkLabel(ear_hdr, text="0.00", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_ear_val.pack(side="right")

        self.bar_ear = ctk.CTkProgressBar(ear_box, height=8, corner_radius=4, fg_color="#1A2438", progress_color=ACCENT_EMERALD)
        self.bar_ear.pack(fill="x", padx=10, pady=(4, 2))
        self.bar_ear.set(0.7)

        self.lbl_ear_sub = ctk.CTkLabel(ear_box, text=f"Threshold: {EAR_THRESHOLD} | State: OPEN", font=ctk.CTkFont(family="Segoe UI", size=9), text_color=TEXT_DIM)
        self.lbl_ear_sub.pack(anchor="w", padx=10, pady=(0, 6))

        # 2. MAR Gauge Box
        mar_box = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        mar_box.pack(fill="x", padx=10, pady=4)

        mar_hdr = ctk.CTkFrame(mar_box, fg_color="transparent")
        mar_hdr.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(mar_hdr, text="MOUTH ASPECT RATIO (MAR)", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=TEXT_SECONDARY).pack(side="left")
        self.lbl_mar_val = ctk.CTkLabel(mar_hdr, text="0.00", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_mar_val.pack(side="right")

        self.bar_mar = ctk.CTkProgressBar(mar_box, height=8, corner_radius=4, fg_color="#1A2438", progress_color=ACCENT_CYAN)
        self.bar_mar.pack(fill="x", padx=10, pady=(4, 2))
        self.bar_mar.set(0.2)

        self.lbl_mar_sub = ctk.CTkLabel(mar_box, text=f"Threshold: {MAR_THRESHOLD} | Status: Nominal", font=ctk.CTkFont(family="Segoe UI", size=9), text_color=TEXT_DIM)
        self.lbl_mar_sub.pack(anchor="w", padx=10, pady=(0, 6))

        # Compatibility aliases for tests & inspectors
        self.val_ear = self.lbl_ear_val
        self.val_mar = self.lbl_mar_val

        # 3. Microsleep Buffer (Closed Frames)
        closure_box = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        closure_box.pack(fill="x", padx=10, pady=4)

        closure_hdr = ctk.CTkFrame(closure_box, fg_color="transparent")
        closure_hdr.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(closure_hdr, text="MICROSLEEP EYE CLOSURE", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=TEXT_SECONDARY).pack(side="left")
        self.lbl_closed_frames = ctk.CTkLabel(closure_hdr, text="0 / 45 f", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_closed_frames.pack(side="right")

        self.bar_closed = ctk.CTkProgressBar(closure_box, height=8, corner_radius=4, fg_color="#1A2438", progress_color=ACCENT_RED)
        self.bar_closed.pack(fill="x", padx=10, pady=(4, 6))
        self.bar_closed.set(0.0)

        # 4. Yawn Counter Segments
        yawn_box = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        yawn_box.pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkLabel(yawn_box, text="FATIGUE YAWN COUNTER", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(6, 4))

        seg_frame = ctk.CTkFrame(yawn_box, fg_color="transparent")
        seg_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.seg1 = ctk.CTkLabel(seg_frame, text="YAWN 1", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), fg_color="#1E293B", text_color=TEXT_DIM, corner_radius=4, width=65, height=22)
        self.seg1.pack(side="left", padx=2, expand=True, fill="x")

        self.seg2 = ctk.CTkLabel(seg_frame, text="YAWN 2", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), fg_color="#1E293B", text_color=TEXT_DIM, corner_radius=4, width=65, height=22)
        self.seg2.pack(side="left", padx=2, expand=True, fill="x")

        self.seg3 = ctk.CTkLabel(seg_frame, text="DANGER", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), fg_color="#1E293B", text_color=TEXT_DIM, corner_radius=4, width=65, height=22)
        self.seg3.pack(side="left", padx=2, expand=True, fill="x")

    def _build_emergency_console(self):
        """Emergency, countdown, and subsystem status card."""
        frame = ctk.CTkFrame(self.right_panel, fg_color=CARD_SURFACE, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        frame.pack(fill="x", padx=8, pady=6)

        hdr_row = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            hdr_row,
            text="EMERGENCY SOS SUBSYSTEM",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_AMBER
        ).pack(side="left")

        # Digital Countdown Display Box
        cd_box = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=8, border_color=CARD_BORDER, border_width=1)
        cd_box.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(cd_box, text="DRIVER RESPONSE TIMER", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color=TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(6, 0))

        self.lbl_countdown_big = ctk.CTkLabel(
            cd_box,
            text="STANDBY (10s)",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_DIM
        )
        self.lbl_countdown_big.pack(pady=(2, 6))

        # Subsystem rows
        self.lbl_alarm_state = self._create_status_row(frame, "Acoustic Warning Siren", "STANDBY", TEXT_SECONDARY)
        self.lbl_hazard_state = self._create_status_row(frame, "Hazard Warning Lights", "OFF", TEXT_SECONDARY)
        self.lbl_photo_state = self._create_status_row(frame, "Incident Snapshot", "READY", TEXT_SECONDARY)
        self.lbl_sms_state = self._create_status_row(frame, "Alert Dispatcher", "Mock SMS (Simulated)", ACCENT_CYAN)

    def _create_status_row(self, parent, label, default_value, color=TEXT_PRIMARY):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_SECONDARY).pack(side="left")
        val_lbl = ctk.CTkLabel(row, text=default_value, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=color)
        val_lbl.pack(side="right")
        return val_lbl

    def _build_location_card(self):
        """Satellite GPS positioning card."""
        frame = ctk.CTkFrame(self.right_panel, fg_color=CARD_SURFACE, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        frame.pack(fill="x", padx=8, pady=6)

        hdr_row = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            hdr_row,
            text="SATELLITE POSITIONING (DEVICE GPS)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="left")

        self.lbl_gps_coords = self._create_status_row(frame, "Fix Coordinates", "Acquiring...", TEXT_SECONDARY)
        self.lbl_gps_accuracy = self._create_status_row(frame, "Horizontal Accuracy", "--", TEXT_DIM)

        self.btn_maps = ctk.CTkButton(
            frame,
            text="🌐  Launch Satellite Maps",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._open_maps_url,
            height=30
        )
        self.btn_maps.pack(fill="x", padx=10, pady=(6, 8))

    def _build_flight_stats(self):
        """Flight recorder stats summary."""
        frame = ctk.CTkFrame(self.right_panel, fg_color=CARD_SURFACE, corner_radius=10, border_color=CARD_BORDER, border_width=1)
        frame.pack(fill="x", padx=8, pady=(6, 10))

        hdr_row = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            hdr_row,
            text="SESSION FLIGHT AUDIT STATS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        stats = get_event_statistics()
        self.lbl_stat_yawns = self._create_status_row(frame, "Total Yawn Triggers", str(stats.get("total_yawns", 0)))
        self.lbl_stat_drowsy = self._create_status_row(frame, "Microsleep Events", str(stats.get("drowsiness_events", 0)))
        self.lbl_stat_emerg = self._create_status_row(frame, "Emergency SOS Activations", str(stats.get("emergency_events", 0)))

    def _build_controls(self):
        """Bottom tactical action bar."""
        self.ctrl_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12, border_color=CARD_BORDER, border_width=1)
        self.ctrl_frame.pack(fill="x", padx=16, pady=(6, 12))

        # Big Reset Button (R)
        self.btn_reset = ctk.CTkButton(
            self.ctrl_frame,
            text="🛡️  RESET SAFETY SYSTEM (R)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#1E3A8A",
            hover_color="#2563EB",
            height=40,
            command=self._on_reset_pressed
        )
        self.btn_reset.pack(side="left", padx=(14, 8), pady=8)

        # View History Button
        self.btn_history = ctk.CTkButton(
            self.ctrl_frame,
            text="📋  View Telemetry Flight Log",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            height=40,
            command=self._open_history_dialog
        )
        self.btn_history.pack(side="left", padx=8, pady=8)

        # Quit Button (Q)
        self.btn_quit = ctk.CTkButton(
            self.ctrl_frame,
            text="POWER OFF (Q)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#450A0A",
            hover_color="#7F1D1D",
            height=40,
            command=self._on_quit_pressed
        )
        self.btn_quit.pack(side="right", padx=(8, 14), pady=8)

    def _bind_keys(self):
        self.bind("<r>", lambda event: self._on_reset_pressed())
        self.bind("<R>", lambda event: self._on_reset_pressed())
        self.bind("<q>", lambda event: self._on_quit_pressed())
        self.bind("<Q>", lambda event: self._on_quit_pressed())
        self.protocol("WM_DELETE_WINDOW", self._on_quit_pressed)

    def _on_reset_pressed(self):
        if self.on_reset_callback:
            self.on_reset_callback()

    def _on_quit_pressed(self):
        if self.on_quit_callback:
            self.on_quit_callback()
        self.destroy()

    def _open_maps_url(self):
        if self.last_maps_url and "maps" in self.last_maps_url:
            webbrowser.open(self.last_maps_url)

    def _open_history_dialog(self):
        EventHistoryDialog(self)

    def update_frame(self, frame):
        """Updates the video feed canvas smoothly with dynamic container scaling."""
        if frame is None or not self.winfo_exists():
            return

        try:
            lbl_w = self.video_container.winfo_width()
            lbl_h = self.video_container.winfo_height()

            if lbl_w < 100 or lbl_h < 100:
                lbl_w = 640
                lbl_h = 440

            h, w, _ = frame.shape
            scale = min((lbl_w - 6) / max(w, 1), (lbl_h - 6) / max(h, 1))
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
        """Updates dashboard gauges, visual progress bars, and emergency alerts."""
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

        # 1. EAR Gauge
        self.lbl_ear_val.configure(text=f"{ear:.2f}")
        ear_norm = min(1.0, max(0.0, ear / 0.40))
        self.bar_ear.set(ear_norm)
        if ear < EAR_THRESHOLD:
            self.bar_ear.configure(progress_color=ACCENT_RED)
            self.lbl_ear_sub.configure(text=f"CRITICAL: <{EAR_THRESHOLD} | State: {state}", text_color=ACCENT_RED)
        elif ear < 0.26:
            self.bar_ear.configure(progress_color=ACCENT_AMBER)
            self.lbl_ear_sub.configure(text=f"WARNING: Approaching {EAR_THRESHOLD} | {state}", text_color=ACCENT_AMBER)
        else:
            self.bar_ear.configure(progress_color=ACCENT_EMERALD)
            self.lbl_ear_sub.configure(text=f"Safe: >{EAR_THRESHOLD} | State: {state}", text_color=TEXT_DIM)

        # 2. MAR Gauge
        self.lbl_mar_val.configure(text=f"{mar:.2f}")
        mar_norm = min(1.0, max(0.0, mar / 0.80))
        self.bar_mar.set(mar_norm)
        if mar >= MAR_THRESHOLD:
            self.bar_mar.configure(progress_color=ACCENT_RED)
            self.lbl_mar_sub.configure(text=f"YAWNING DETECTED: >={MAR_THRESHOLD}", text_color=ACCENT_RED)
        elif mar >= 0.35:
            self.bar_mar.configure(progress_color=ACCENT_AMBER)
            self.lbl_mar_sub.configure(text=f"Mouth Open: Approaching {MAR_THRESHOLD}", text_color=ACCENT_AMBER)
        else:
            self.bar_mar.configure(progress_color=ACCENT_CYAN)
            self.lbl_mar_sub.configure(text=f"Nominal: <{MAR_THRESHOLD}", text_color=TEXT_DIM)

        # 3. Microsleep Buffer
        self.lbl_closed_frames.configure(text=f"{closed} / 45 f")
        self.bar_closed.set(min(1.0, closed / 45.0))

        # 4. Yawn Segment Indicators
        self.seg1.configure(
            fg_color=ACCENT_AMBER if yawns >= 1 else "#1E293B",
            text_color="#000000" if yawns >= 1 else TEXT_DIM
        )
        self.seg2.configure(
            fg_color=ACCENT_AMBER if yawns >= 2 else "#1E293B",
            text_color="#000000" if yawns >= 2 else TEXT_DIM
        )
        self.seg3.configure(
            fg_color=ACCENT_RED if yawns >= 3 else "#1E293B",
            text_color="#FFFFFF" if yawns >= 3 else TEXT_DIM
        )

        # 5. GPS Location
        if location_obj and location_obj.is_available:
            self.lbl_gps_coords.configure(text=f"{location_obj.latitude:.5f}° N, {location_obj.longitude:.5f}° E", text_color=ACCENT_EMERALD)
            acc_str = f"±{location_obj.accuracy:.0f}m (Civilian GPS Fix)" if location_obj.accuracy else "Civilian Fix"
            self.lbl_gps_accuracy.configure(text=acc_str, text_color=TEXT_PRIMARY)
            self.last_maps_url = location_obj.maps_url
            self.btn_maps.configure(state="normal", text="🌐  Launch Satellite Maps")
        else:
            self.lbl_gps_coords.configure(text="Unavailable", text_color=TEXT_SECONDARY)
            self.lbl_gps_accuracy.configure(text="No GPS permission or signal", text_color=TEXT_DIM)
            self.btn_maps.configure(state="disabled", text="🌐  Location Unavailable")

        # 6. Emergency & Countdown States
        is_emergency = emerg_status.get("is_emergency", False)
        countdown_active = emerg_status.get("countdown_active", False)
        rem_time = emerg_status.get("remaining_time", RESPONSE_TIMEOUT_SECONDS)
        danger_reason = emerg_status.get("danger_reason", "")
        alarm_on = emerg_status.get("alarm_active", False)
        hazard_on = emerg_status.get("hazard_lights", False)
        notif_status = emerg_status.get("notification_status", "IDLE")
        provider = emerg_status.get("provider_name", "Mock SMS")

        self.lbl_alarm_state.configure(
            text="● LOUD SIREN ON" if alarm_on else "STANDBY",
            text_color=ACCENT_RED if alarm_on else TEXT_SECONDARY
        )

        # Pulsing Hazard indicator
        if hazard_on:
            self._hazard_flash_state = not self._hazard_flash_state
            flash_col = ACCENT_AMBER if self._hazard_flash_state else "#78350F"
            self.lbl_hazard_state.configure(text="◄◄ FLASHING (ON) ►►", text_color=flash_col)
        else:
            self.lbl_hazard_state.configure(text="OFF", text_color=TEXT_SECONDARY)

        self.lbl_photo_state.configure(text=emerg_status.get("photo_status", "READY"))
        self.lbl_sms_state.configure(
            text=f"{provider}: {notif_status}",
            text_color=ACCENT_EMERALD if notif_status in ("SIMULATED", "SENT") else (ACCENT_RED if notif_status == "FAILED" else TEXT_SECONDARY)
        )

        # Visual Banner & Countdown Formatting
        if is_emergency:
            self.status_pill.configure(text="🚨 CRITICAL SOS: ACTIVATED", fg_color=ACCENT_RED, text_color="#FFFFFF")
            self.alert_banner.configure(fg_color="#450A0A")
            self.alert_banner_text.configure(
                text=f"🚨 [ EMERGENCY ] DRIVER UNRESPONSIVE — SOS DISPATCHED ({notif_status}) — PRESS 'R' TO CANCEL",
                text_color="#FEF2F2"
            )
            self.lbl_countdown_big.configure(text="00:00 (SOS DISPATCHED)", text_color=ACCENT_RED)
            self.btn_reset.configure(fg_color=ACCENT_RED, hover_color="#B91C1C")

        elif countdown_active:
            self.status_pill.configure(text="▲ ATTENTION REQUIRED", fg_color=ACCENT_AMBER, text_color="#000000")
            self.alert_banner.configure(fg_color="#3B1700")
            self.alert_banner_text.configure(
                text=f"⚠️ {danger_reason.upper()} — RESPOND IN {rem_time}s (PRESS 'R')",
                text_color=ACCENT_AMBER
            )
            self.lbl_countdown_big.configure(text=f"00:{rem_time:02d}s REMAINING", text_color=ACCENT_AMBER)
            self.btn_reset.configure(fg_color=ACCENT_AMBER, hover_color="#D97706")

        elif drowsy or yawns > 0:
            self.status_pill.configure(text="● ATTENTION REQUIRED", fg_color="#CA8A04", text_color="#000000")
            self.alert_banner.configure(fg_color=CARD_SURFACE)
            self.alert_banner_text.configure(text=f"Notice: Yawn count: {yawns} / {YAWN_LIMIT}", text_color=ACCENT_AMBER)
            self.lbl_countdown_big.configure(text="STANDBY (10s)", text_color=TEXT_DIM)
            self.btn_reset.configure(fg_color="#1E3A8A", hover_color="#2563EB")

        else:
            self.status_pill.configure(text="● AUTOPILOT GUARD: NOMINAL", fg_color=ACCENT_EMERALD, text_color="#000000")
            self.alert_banner.configure(fg_color=CARD_SURFACE)
            self.alert_banner_text.configure(text="[ SAFE ] Driver Attentive — All Telemetry Nominal", text_color=ACCENT_EMERALD)
            self.lbl_countdown_big.configure(text="STANDBY (10s)", text_color=TEXT_DIM)
            self.btn_reset.configure(fg_color="#1E3A8A", hover_color="#2563EB")
