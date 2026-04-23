#!/usr/bin/env python3
"""
GUI for Issue Agent - A beautiful blue interface with guitars for interacting with the webhook system.

This GUI provides a visual interface to:
- Monitor incoming webhooks
- View recent issues
- Manually trigger agent responses
- View system status
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
from datetime import datetime
import threading
import os
from typing import Optional


class IssueAgentGUI:
    """Main GUI application for Issue Agent."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Issue Agent - Webhook Controller")
        self.root.geometry("900x700")
        
        # Beautiful blue color scheme
        self.bg_color = "#1e3a5f"  # Deep blue
        self.accent_color = "#4a90e2"  # Bright blue
        self.text_color = "#ffffff"
        self.button_color = "#2c5f8d"
        
        self.root.configure(bg=self.bg_color)
        
        # API endpoint (default to localhost)
        self.api_base = os.getenv("ISSUE_AGENT_URL", "http://localhost:8000")
        
        self.setup_ui()
        self.refresh_status()
    
    def setup_ui(self):
        """Set up the user interface with guitars and blue theme."""
        
        # Title with guitars
        title_frame = tk.Frame(self.root, bg=self.bg_color)
        title_frame.pack(pady=20, padx=20, fill=tk.X)
        
        # Guitar emoji/symbol decorations (3 guitars as demanded!)
        guitar1 = tk.Label(title_frame, text="🎸", font=("Arial", 48), bg=self.bg_color)
        guitar1.pack(side=tk.LEFT, padx=10)
        
        title = tk.Label(
            title_frame,
            text="Issue Agent Control Panel",
            font=("Arial", 24, "bold"),
            bg=self.bg_color,
            fg=self.text_color
        )
        title.pack(side=tk.LEFT, expand=True)
        
        guitar2 = tk.Label(title_frame, text="🎸", font=("Arial", 48), bg=self.bg_color)
        guitar2.pack(side=tk.LEFT, padx=10)
        
        # Subtitle with third guitar
        subtitle_frame = tk.Frame(self.root, bg=self.bg_color)
        subtitle_frame.pack(pady=5)
        
        subtitle = tk.Label(
            subtitle_frame,
            text="🎸 Webhook Management & Monitoring 🎸",
            font=("Arial", 12),
            bg=self.bg_color,
            fg=self.accent_color
        )
        subtitle.pack()
        
        # Status section
        status_frame = tk.LabelFrame(
            self.root,
            text="System Status",
            font=("Arial", 12, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            bd=2,
            relief=tk.GROOVE
        )
        status_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame,
            text="Status: Checking...",
            font=("Arial", 11),
            bg=self.bg_color,
            fg=self.accent_color,
            anchor=tk.W
        )
        self.status_label.pack(pady=10, padx=10, fill=tk.X)
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.refresh_btn = tk.Button(
            button_frame,
            text="🔄 Refresh Status",
            command=self.refresh_status,
            bg=self.button_color,
            fg=self.text_color,
            font=("Arial", 11, "bold"),
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.test_webhook_btn = tk.Button(
            button_frame,
            text="🎯 Test Webhook",
            command=self.test_webhook,
            bg=self.button_color,
            fg=self.text_color,
            font=("Arial", 11, "bold"),
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10
        )
        self.test_webhook_btn.pack(side=tk.LEFT, padx=5)
        
        # Activity log
        log_frame = tk.LabelFrame(
            self.root,
            text="Activity Log",
            font=("Arial", 12, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            bd=2,
            relief=tk.GROOVE
        )
        log_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#0d1b2a",
            fg="#00ff00",
            insertbackground=self.text_color,
            relief=tk.SUNKEN,
            bd=2
        )
        self.log_text.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        
        # Configuration section
        config_frame = tk.LabelFrame(
            self.root,
            text="Configuration",
            font=("Arial", 12, "bold"),
            bg=self.bg_color,
            fg=self.text_color,
            bd=2,
            relief=tk.GROOVE
        )
        config_frame.pack(pady=10, padx=20, fill=tk.X)
        
        url_label = tk.Label(
            config_frame,
            text="API Endpoint:",
            bg=self.bg_color,
            fg=self.text_color,
            font=("Arial", 10)
        )
        url_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.url_entry = tk.Entry(
            config_frame,
            font=("Arial", 10),
            bg="#0d1b2a",
            fg=self.text_color,
            insertbackground=self.text_color,
            width=40
        )
        self.url_entry.insert(0, self.api_base)
        self.url_entry.pack(side=tk.LEFT, padx=10, pady=10)
        
        update_url_btn = tk.Button(
            config_frame,
            text="Update",
            command=self.update_api_url,
            bg=self.button_color,
            fg=self.text_color,
            font=("Arial", 10, "bold")
        )
        update_url_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Initial log message
        self.log("Issue Agent GUI initialized 🎸")
        self.log(f"API endpoint: {self.api_base}")
    
    def log(self, message: str):
        """Add a message to the activity log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def update_api_url(self):
        """Update the API base URL."""
        new_url = self.url_entry.get().strip()
        if new_url:
            self.api_base = new_url
            self.log(f"API endpoint updated to: {new_url}")
            self.refresh_status()
        else:
            messagebox.showerror("Error", "Please enter a valid URL")
    
    def refresh_status(self):
        """Refresh the system status."""
        self.log("Refreshing system status...")
        
        def check_status():
            try:
                response = requests.get(f"{self.api_base}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    status_text = f"Status: ✅ Online | {data.get('status', 'unknown')}"
                    self.status_label.config(text=status_text, fg="#00ff00")
                    self.log("System is online and healthy")
                else:
                    self.status_label.config(
                        text=f"Status: ⚠️ Response {response.status_code}",
                        fg="#ffaa00"
                    )
                    self.log(f"Unexpected response: {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.status_label.config(
                    text="Status: ❌ Offline or unreachable",
                    fg="#ff0000"
                )
                self.log(f"Error connecting to API: {str(e)}")
        
        # Run in background thread to avoid blocking UI
        threading.Thread(target=check_status, daemon=True).start()
    
    def test_webhook(self):
        """Send a test webhook to the system."""
        self.log("Sending test webhook...")
        
        def send_test():
            try:
                # Create a simple test payload
                test_payload = {
                    "action": "opened",
                    "issue": {
                        "number": 9999,
                        "title": "Test Issue from GUI",
                        "body": "This is a test issue sent from the Issue Agent GUI 🎸",
                        "user": {"login": "gui-user"},
                        "html_url": "https://github.com/test/test/issues/9999"
                    },
                    "repository": {
                        "full_name": "test/test",
                        "html_url": "https://github.com/test/test"
                    }
                }
                
                response = requests.post(
                    f"{self.api_base}/webhook",
                    json=test_payload,
                    headers={"X-GitHub-Event": "issues"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.log("✅ Test webhook sent successfully")
                    messagebox.showinfo(
                        "Success",
                        "Test webhook sent successfully!\n\nCheck your GitHub repository for the response."
                    )
                else:
                    self.log(f"⚠️ Webhook response: {response.status_code}")
                    messagebox.showwarning(
                        "Warning",
                        f"Webhook returned status {response.status_code}\n\n{response.text}"
                    )
            except requests.exceptions.RequestException as e:
                self.log(f"❌ Error sending webhook: {str(e)}")
                messagebox.showerror(
                    "Error",
                    f"Failed to send test webhook:\n\n{str(e)}"
                )
        
        # Run in background thread
        threading.Thread(target=send_test, daemon=True).start()


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = IssueAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
