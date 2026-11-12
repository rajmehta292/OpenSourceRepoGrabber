"""
OpenSource Repo Grabber - Complete GUI with Overview, Trending, Search, OSS Launchpad & AI
"""
import os
import threading
import logging
import webbrowser
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox, filedialog

import config
from repo_manager import get_repo_manager
from ollama_client import get_ollama_client
from github_api import get_github_client, CURATED_STARTER_REPOS, LICENSE_KNOWLEDGE_BASE
from contributor_guide import FIRST_PR_WORKFLOW, GIT_ESSENTIALS, CONVENTIONAL_COMMITS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToolTipManager:
    """Singleton to manage a single tooltip window for the entire app with debouncing."""
    _instance = None

    def __init__(self, root):
        self.root = root
        self.tip_window = None
        self.active_widget = None
        self.show_id = None
        self.is_shown = False
        self._is_active = True

    @classmethod
    def get_instance(cls, root=None):
        if cls._instance is None and root is not None:
            cls._instance = cls(root)
        return cls._instance

    def show(self, widget, text):
        if not text:
            self.hide()
            return
            
        if self.active_widget == widget and self.is_shown:
            return

        self._cancel_pending()
        self._is_active = True
        self.show_id = self.root.after(250, lambda: self._actual_show(widget, text))

    def _actual_show(self, widget, text):
        if not self._is_active:
            return
        self.hide()
        
        self._is_active = True
        self.active_widget = widget
        
        x = widget.winfo_rootx() + widget.winfo_width() + 10
        y = widget.winfo_rooty() + (widget.winfo_height() // 4)
        
        try:
            self.tip_window = tw = ctk.CTkToplevel(self.root)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.configure(fg_color=("#F2F0E6", "#151D18"))
            tw.attributes("-topmost", True)
            
            label = ctk.CTkLabel(
                tw, text=text, justify="left",
                padx=12, pady=8, font=ctk.CTkFont(family="Inter", size=12)
            )
            label.pack()
            self.is_shown = True
        except Exception as e:
            logger.error(f"Error showing tooltip: {e}")
            self.hide()

    def _cancel_pending(self):
        self._is_active = False
        if self.show_id:
            try:
                self.root.after_cancel(self.show_id)
            except Exception:
                pass
            self.show_id = None

    def hide(self):
        self._cancel_pending()
        if self.tip_window:
            try:
                self.tip_window.withdraw()
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None
            
        self.active_widget = None
        self.is_shown = False


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<FocusOut>", self.on_leave)
        self.widget.bind("<ButtonPress>", self.on_leave)
        self.widget.bind("<ButtonRelease>", self.on_leave)
        self.widget.bind("<KeyPress>", self.on_leave)
        self.widget.bind("<KeyRelease>", self.on_leave)

    def on_enter(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager:
            manager.show(self.widget, self.text)

    def on_leave(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager:
            manager.hide()


ctk.set_appearance_mode(config.DEFAULT_APPEARANCE_MODE)
if os.path.exists(config.THEME_PATH):
    ctk.set_default_color_theme(str(config.THEME_PATH))
else:
    ctk.set_default_color_theme("blue")


class RepoGrabberApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OSRG - OpenSource Repo Grabber & Intelligence Hub")
        self.geometry(f"{config.WINDOW_DEFAULT_WIDTH}x{config.WINDOW_DEFAULT_HEIGHT}")
        self.minsize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)

        # Set official application icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                logger.debug(f"Could not set window icon: {e}")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ToolTipManager.get_instance(self)
        
        self.bind("<FocusOut>", self._on_app_focus_out)
        self.bind("<Unmap>", self._on_app_minimize)
        self.bind("<Configure>", self._on_app_configure)
        self.bind("<KeyPress>", self._on_key_press)

        # Initialize managers
        self.repo_manager = get_repo_manager()
        self.ollama = get_ollama_client()
        self.github = get_github_client()
        
        self.repos = []
        self.trending_repos = []
        self.search_results = []
        self.good_first_issues = []
        self.current_repo = None

        self._create_sidebar()
        self._create_main_content()
        self._load_repos()

    def _on_app_focus_out(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()

    def _on_app_minimize(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()

    def _on_app_configure(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()

    def _on_key_press(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="OSRG",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
            text_color=("#2C342C", "#10B981")
        )
        self.logo_label.pack(pady=(40, 25), padx=24, anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("overview", "Overview Hub"),
            ("repos", "Repositories"),
            ("trending", "Trending"),
            ("search", "Search"),
            ("learner", "OSS Launchpad"),
            ("add", "Add New"),
            ("ai", "AI Explain"),
            ("settings", "Settings")
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=36,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray20", "gray85"),
                hover_color=("gray90", "gray30"),
                command=lambda k=key: self._switch_view(k)
            )
            btn.pack(fill="x", padx=15, pady=2)
            self.nav_buttons[key] = btn
            
            tip_map = {
                "overview": "Welcome Hub, live metrics, and curated starter repositories",
                "repos": "Manage locally cloned repositories and file trees",
                "trending": "Discover trending open-source projects on GitHub",
                "search": "Search 50M+ repositories with license filters",
                "learner": "Good First Issues, interactive License Decoder, and PR guides",
                "add": "Import any repository by URL or owner/name",
                "ai": "Analyze code with Project Oracle AI or Heuristic Engine",
                "settings": "Configure local storage, editors, and AI engines"
            }
            ToolTip(btn, tip_map.get(key, ""))

        # Bottom section: Theme toggle and folder
        spacer = ctk.CTkLabel(self.sidebar, text="")
        spacer.pack(fill="both", expand=True)

        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(theme_frame, text="Night Mode", font=ctk.CTkFont(size=12)).pack(side="left")
        
        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="",
            width=40,
            command=self._toggle_theme
        )
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="right")

        ctk.CTkButton(
            self.sidebar,
            text="Open Repos Path",
            height=30,
            corner_radius=8,
            fg_color=("gray90", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray85", "gray35"),
            command=self._open_repos_folder
        ).pack(pady=(0, 20), padx=15, fill="x")

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def _create_main_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        
        self.views = {}
        
        self._create_overview_view()
        self._create_repos_view()
        self._create_trending_view()
        self._create_search_view()
        self._create_learner_view()
        self._create_add_view()
        self._create_ai_view()
        self._create_settings_view()
        
        self._switch_view("overview")

    # ==========================================
    # 1. OVERVIEW & WELCOME HUB (FTUX)
    # ==========================================
    def _create_overview_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["overview"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(25, 10))
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        
        ctk.CTkLabel(
            title_box,
            text="OpenSource Repo Grabber",
            font=ctk.CTkFont(family="Inter", size=26, weight="bold"),
            text_color=("#1D1D1F", "#ECF0ED")
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_box,
            text="Your Command Center to discover, audit, learn, and contribute to top open-source projects.",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=("gray50", "gray65")
        ).pack(anchor="w", pady=(2, 0))

        status_box = ctk.CTkFrame(header, fg_color="transparent")
        status_box.pack(side="right")

        ctk.CTkButton(
            status_box,
            text="🔑 Set PAT",
            width=90,
            height=36,
            corner_radius=10,
            fg_color=("gray90", "#202924"),
            text_color=("#1D1D1F", "#ECF0ED"),
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self._prompt_github_token
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            status_box,
            text="🔄 Refresh Hub",
            width=120,
            height=36,
            corner_radius=10,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", weight="bold"),
            command=self._refresh_overview
        ).pack(side="left", padx=5)

        # Dynamic Metrics KPI Grid
        self.overview_kpi_frame = ctk.CTkFrame(view, fg_color="transparent")
        self.overview_kpi_frame.pack(fill="x", padx=25, pady=15)
        self._render_overview_kpis()

        # Three User Archetypes Guide Banner
        personas_card = ctk.CTkFrame(view, corner_radius=14, fg_color=("#F5F7F3", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
        personas_card.pack(fill="x", padx=25, pady=10)
        
        ctk.CTkLabel(
            personas_card,
            text="🎯 Tailored for Every Developer Journey",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=("#2C342C", "#10B981")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        personas_grid = ctk.CTkFrame(personas_card, fg_color="transparent")
        personas_grid.pack(fill="x", padx=15, pady=(0, 15))
        personas_grid.grid_columnconfigure((0, 1, 2), weight=1)

        p1 = ctk.CTkFrame(personas_grid, corner_radius=10, fg_color=("#FFFFFF", "#1E2621"))
        p1.grid(row=0, column=0, padx=6, pady=5, sticky="nsew")
        ctk.CTkLabel(p1, text="⚡ The Tinkerer", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(p1, text="Instant README previews, directory tree inspection without heavy cloning, and AI code breakdowns.", wraplength=220, justify="left", font=ctk.CTkFont(size=11), text_color=("gray40", "gray70")).pack(anchor="w", padx=12, pady=(0, 10))

        p2 = ctk.CTkFrame(personas_grid, corner_radius=10, fg_color=("#FFFFFF", "#1E2621"))
        p2.grid(row=0, column=1, padx=6, pady=5, sticky="nsew")
        ctk.CTkLabel(p2, text="🏗️ The Builder & Architect", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(p2, text="Multi-file Project Oracle audits, pattern detection (MVC, Microservices), smart tagging, and IDE launch.", wraplength=220, justify="left", font=ctk.CTkFont(size=11), text_color=("gray40", "gray70")).pack(anchor="w", padx=12, pady=(0, 10))

        p3 = ctk.CTkFrame(personas_grid, corner_radius=10, fg_color=("#FFFFFF", "#1E2621"))
        p3.grid(row=0, column=2, padx=6, pady=5, sticky="nsew")
        ctk.CTkLabel(p3, text="🌱 The OSS Contributor", font=ctk.CTkFont(family="Inter", size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(p3, text="Good First Issues finder, plain-English License Decoder, and step-by-step first PR checklists.", wraplength=220, justify="left", font=ctk.CTkFont(size=11), text_color=("gray40", "gray70")).pack(anchor="w", padx=12, pady=(0, 10))

        # Quick Actions Row
        actions_frame = ctk.CTkFrame(view, fg_color="transparent")
        actions_frame.pack(fill="x", padx=25, pady=10)
        
        ctk.CTkLabel(actions_frame, text="⚡ Quick Actions", font=ctk.CTkFont(family="Inter", size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
        
        btns_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btns_row.pack(fill="x")
        
        q_actions = [
            ("🔥 Trending Repos", "trending", ("#5E6C54", "#10B981")),
            ("🔍 Search GitHub", "search", ("gray90", "#202924")),
            ("🌱 Good First Issues", "learner", ("gray90", "#202924")),
            ("➕ Import by URL", "add", ("gray90", "#202924")),
            ("🧠 AI Analysis Agent", "ai", ("gray90", "#202924"))
        ]
        for label, view_key, col in q_actions:
            tc = "white" if col[0] != "gray90" else ("#1D1D1F", "#ECF0ED")
            b = ctk.CTkButton(
                btns_row,
                text=label,
                height=36,
                corner_radius=8,
                fg_color=col,
                text_color=tc,
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                command=lambda k=view_key: self._switch_view(k)
            )
            b.pack(side="left", padx=(0, 8))

        # Featured Starter Repositories Section
        starters_frame = ctk.CTkFrame(view, fg_color="transparent")
        starters_frame.pack(fill="x", padx=25, pady=(15, 25))
        
        ctk.CTkLabel(starters_frame, text="⭐ Curated Starter Projects (1-Click Explore)", font=ctk.CTkFont(family="Inter", size=16, weight="bold")).pack(anchor="w", pady=(0, 8))
        
        for starter in CURATED_STARTER_REPOS[:4]:
            self._create_starter_card(starters_frame, starter)

    def _render_overview_kpis(self):
        for w in self.overview_kpi_frame.winfo_children():
            w.destroy()
        
        self.overview_kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        cloned_count = len(self.repos)
        folders_dict = self.repo_manager.get_all_license_folders()
        active_folders = sum(1 for f in folders_dict.values() if f.get("count", 0) > 0)
        
        rate_info = self.github.get_rate_limit_status()
        rate_rem = rate_info.get("remaining", 60)
        rate_lim = rate_info.get("limit", 60)
        rate_auth = rate_info.get("authenticated", False)
        rate_text = f"{rate_rem}/{rate_lim} req"
        rate_sub = "Authenticated PAT" if rate_auth else "Rate Guard Active"

        ollama_ok = self.ollama.is_available()
        engine_str = "Ollama Active" if ollama_ok else "Heuristic Engine"
        engine_col = "#10B981" if ollama_ok else "#F59E0B"
        
        kpis = [
            ("📁 Cloned Projects", str(cloned_count), "In local license folders"),
            ("⚖️ Active License Buckets", str(active_folders), "Organized by SPDX"),
            ("🌐 GitHub API Quota", rate_text, rate_sub),
            ("🧠 Architecture AI", engine_str, "Oracle auditing active")
        ]
        
        for i, (title, val, subtitle) in enumerate(kpis):
            box = ctk.CTkFrame(self.overview_kpi_frame, corner_radius=12, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
            box.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            
            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(family="Inter", size=11, weight="bold"), text_color=("gray50", "gray65")).pack(anchor="w", padx=15, pady=(12, 2))
            ctk.CTkLabel(box, text=val, font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color=engine_col if i == 3 else ("#1D1D1F", "#ECF0ED")).pack(anchor="w", padx=15)
            ctk.CTkLabel(box, text=subtitle, font=ctk.CTkFont(family="Inter", size=10), text_color=("gray40", "gray60")).pack(anchor="w", padx=15, pady=(2, 12))

    def _create_starter_card(self, parent, starter):
        card = ctk.CTkFrame(parent, height=80, corner_radius=10, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
        card.pack(fill="x", pady=5)
        card.grid_propagate(False)
        
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=18, pady=10)
        
        top_line = ctk.CTkFrame(info, fg_color="transparent")
        top_line.pack(fill="x")
        
        ctk.CTkLabel(top_line, text=starter["full_name"], font=ctk.CTkFont(family="Inter", size=15, weight="bold")).pack(side="left")
        ctk.CTkLabel(top_line, text=f"  ● {starter.get('language', 'Polyglot')}  |  ★ {starter.get('stargazers_count', 0):,}  |  {starter.get('license', 'MIT')}", font=ctk.CTkFont(size=11), text_color=config.COLORS["dark"]["accent"]).pack(side="left", padx=8)
        
        desc = starter.get("description", "")
        ctk.CTkLabel(info, text=desc[:110] + ("..." if len(desc) > 110 else ""), font=ctk.CTkFont(size=11), text_color=("gray40", "gray70"), anchor="w").pack(fill="x", pady=(2, 0))
        
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(side="right", padx=15, pady=10)
        
        ctk.CTkButton(
            btn_box,
            text="⚡ 1-Click Clone",
            width=110,
            height=32,
            corner_radius=8,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=lambda s=starter: self._clone_starter_repo(s)
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btn_box,
            text="👁️ Readme",
            width=80,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("#5E6C54", "#10B981"),
            text_color=("#5E6C54", "#10B981"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda s=starter: self._preview_remote_readme(s)
        ).pack(side="right", padx=4)
        
        ctk.CTkButton(
            btn_box,
            text="GitHub",
            width=65,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("#D1D5CB", "#202924"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda u=starter.get("html_url"): webbrowser.open(u)
        ).pack(side="right", padx=4)

    def _clone_starter_repo(self, starter):
        url = starter.get("clone_url") or f"https://github.com/{starter['full_name']}.git"
        lic = starter.get("license_spdx_id")
        
        messagebox.showinfo("Cloning", f"Starting clone for {starter['full_name']} into license folder...")
        
        def clone():
            result = self.repo_manager.add_repo(url, license_spdx=lic)
            if result.get("status") == "cloned":
                self.after(0, lambda: messagebox.showinfo("Success", f"Successfully cloned {result['name']}!"))
                self._load_repos()
                self.after(0, self._render_overview_kpis)
            elif result.get("status") == "already_exists":
                self.after(0, lambda: messagebox.showinfo("Info", "Repository already exists in your local collection!"))
            else:
                self.after(0, lambda: messagebox.showerror("Clone Failed", result.get("error", "Unknown error")))

        threading.Thread(target=clone, daemon=True).start()

    def _prompt_github_token(self):
        token_win = ctk.CTkToplevel(self)
        token_win.title("GitHub Personal Access Token (PAT)")
        token_win.geometry("500x240")
        token_win.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(token_win, text="🔑 Configure GitHub Token", font=ctk.CTkFont(family="Inter", size=18, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(token_win, text="Adding a token increases rate limits from 60 to 5,000 requests/hour.", font=ctk.CTkFont(size=12), text_color=("gray50", "gray65")).pack(pady=(0, 15))
        
        token_entry = ctk.CTkEntry(token_win, placeholder_text="ghp_...", width=400, height=36, corner_radius=8)
        token_entry.insert(0, self.github.token)
        token_entry.pack(pady=5)
        
        btn_box = ctk.CTkFrame(token_win, fg_color="transparent")
        btn_box.pack(pady=15)
        
        def save():
            tok = token_entry.get().strip()
            self.github.set_token(tok)
            token_win.destroy()
            self._render_overview_kpis()
            messagebox.showinfo("Success", "GitHub token updated successfully!")
            
        ctk.CTkButton(btn_box, text="Save Token", width=120, height=34, corner_radius=8, command=save).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="Cancel", width=90, height=34, corner_radius=8, fg_color="transparent", border_width=1, command=token_win.destroy).pack(side="left", padx=5)

    def _refresh_overview(self):
        self._load_repos()
        self._render_overview_kpis()

    # ==========================================
    # 2. REPOSITORIES VIEW (Local & Inspected)
    # ==========================================
    def _create_repos_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["repos"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            header,
            text="Local Repositories",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold")
        ).pack(side="left")
        
        ctk.CTkButton(
            header,
            text="Refresh",
            width=80,
            command=self._load_repos
        ).pack(side="right")
        
        ctk.CTkButton(
            header,
            text="Update All",
            width=100,
            command=self._update_all_repos
        ).pack(side="right", padx=10)

        filter_bar = ctk.CTkFrame(view, fg_color="transparent")
        filter_bar.pack(fill="x", padx=20, pady=(5, 10))

        ctk.CTkLabel(filter_bar, text="License:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))
        self.repo_license_filter = ctk.CTkComboBox(
            filter_bar,
            values=["All Licenses", "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "GPL-3.0", "Other"],
            width=140,
            command=lambda x: self._display_repos()
        )
        self.repo_license_filter.set("All Licenses")
        self.repo_license_filter.pack(side="left")

        ctk.CTkLabel(filter_bar, text="Search Local:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(20, 6))
        self.local_search_entry = ctk.CTkEntry(
            filter_bar,
            placeholder_text="Filter local repos by name...",
            width=240,
            height=32
        )
        self.local_search_entry.pack(side="left")
        self.local_search_entry.bind("<KeyRelease>", lambda e: self._display_repos())

        self.repo_list = ctk.CTkFrame(view, fg_color="transparent")
        self.repo_list.pack(fill="both", expand=True, padx=20, pady=10)

    def _load_repos(self):
        def load():
            try:
                self.repos = self.repo_manager.list_repos()
                self.after(0, self._display_repos)
                if hasattr(self, "overview_kpi_frame"):
                    self.after(0, self._render_overview_kpis)
            except Exception as e:
                logger.error(f"Error loading repos: {e}")
        
        threading.Thread(target=load, daemon=True).start()

    def _display_repos(self):
        for widget in self.repo_list.winfo_children():
            widget.destroy()
        
        if not self.repos:
            empty_frame = ctk.CTkFrame(self.repo_list, corner_radius=12, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
            empty_frame.pack(fill="x", padx=10, pady=20)
            
            ctk.CTkLabel(
                empty_frame,
                text="📦 No Cloned Repositories Found Yet",
                font=ctk.CTkFont(family="Inter", size=16, weight="bold")
            ).pack(pady=(20, 5))
            
            ctk.CTkLabel(
                empty_frame,
                text="Get started by cloning curated starters from the Overview Hub, exploring Trending, or importing any GitHub repository.",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray70")
            ).pack(pady=(0, 15))

            btns = ctk.CTkFrame(empty_frame, fg_color="transparent")
            btns.pack(pady=(0, 20))
            
            ctk.CTkButton(
                btns,
                text="Go to Overview Hub",
                width=140,
                command=lambda: self._switch_view("overview")
            ).pack(side="left", padx=5)

            ctk.CTkButton(
                btns,
                text="Add Repository",
                width=140,
                command=lambda: self._switch_view("add")
            ).pack(side="left", padx=5)
            return

        selected_license = getattr(self, "repo_license_filter", None)
        lic_val = selected_license.get() if selected_license else "All Licenses"
        
        search_kw = ""
        if hasattr(self, "local_search_entry"):
            search_kw = self.local_search_entry.get().strip().lower()

        filtered_repos = []
        for r in self.repos:
            if lic_val != "All Licenses" and r.get("license", "").lower() != lic_val.lower():
                continue
            if search_kw and search_kw not in r["name"].lower():
                continue
            filtered_repos.append(r)

        if not filtered_repos:
            ctk.CTkLabel(
                self.repo_list,
                text="No repositories matching current filters.",
                text_color="gray"
            ).pack(pady=30)
            return

        for repo in filtered_repos:
            self._create_repo_card(repo)

    def _create_repo_card(self, repo):
        card = ctk.CTkFrame(self.repo_list, height=140, corner_radius=12, border_width=0)
        card.pack(fill="x", pady=10, padx=10)
        card.grid_propagate(False)
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)
        
        top_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_row.pack(fill="x")
        
        repo_name_lbl = ctk.CTkLabel(
            top_row,
            text=repo["name"],
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            anchor="w"
        )
        repo_name_lbl.pack(side="left")

        lic_badge = ctk.CTkLabel(
            top_row,
            text=f" {repo.get('license', 'License')} ",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color=("#E8EDE6", "#1D2620"),
            text_color=("#5E6C54", "#10B981"),
            corner_radius=4
        )
        lic_badge.pack(side="left", padx=10)
        
        path_lbl = ctk.CTkLabel(
            info_frame,
            text=f"📍 {repo['path']}",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=("gray50", "gray65"),
            anchor="w"
        )
        path_lbl.pack(fill="x", pady=(2, 0))
        
        if repo.get("last_update"):
            sync_lbl = ctk.CTkLabel(
                info_frame,
                text=f"🕒 Last synchronized: {repo['last_update'][:16]}",
                font=ctk.CTkFont(family="Inter", size=10),
                text_color=("gray50", "gray65"),
                anchor="w"
            )
            sync_lbl.pack(fill="x", pady=(2, 0))

        if repo.get("smart_tags"):
            tags_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            tags_frame.pack(fill="x", pady=(6, 0))
            for tag in repo["smart_tags"][:5]:
                t = ctk.CTkLabel(
                    tags_frame,
                    text=f" {tag} ",
                    font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                    fg_color=("#E8EDE6", "#1D2620"),
                    text_color=("#5E6C54", "#10B981"),
                    corner_radius=4
                )
                t.pack(side="left", padx=(0, 6))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", fill="y", padx=15)
        
        inner_btns = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner_btns.pack(expand=True)

        readme_btn = ctk.CTkButton(
            inner_btns,
            text="📖 Readme",
            width=75,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=("#D1D5CB", "#202924"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda r=repo: self._show_readme_modal(r)
        )
        readme_btn.pack(side="left", padx=3)
        ToolTip(readme_btn, "Inspect README.md in app")

        files_btn = ctk.CTkButton(
            inner_btns,
            text="🌳 Files",
            width=70,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=("#D1D5CB", "#202924"),
            text_color=("gray20", "gray85"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda r=repo: self._show_file_tree_modal(r)
        )
        files_btn.pack(side="left", padx=3)
        ToolTip(files_btn, "View project directory tree and statistics")

        audit_btn = ctk.CTkButton(
            inner_btns,
            text="🏛️ Audit",
            width=75,
            height=30,
            corner_radius=6,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=lambda r=repo: self._run_architecture_audit(r)
        )
        audit_btn.pack(side="left", padx=3)
        ToolTip(audit_btn, "Run Project Oracle Architectural Audit")

        open_btn = ctk.CTkButton(
            inner_btns,
            text="💻 Editor",
            width=70,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=("#5E6C54", "#10B981"),
            text_color=("#5E6C54", "#10B981"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda p=repo["path"]: self._open_repo(p)
        )
        open_btn.pack(side="left", padx=3)
        ToolTip(open_btn, "Open source code in Cursor, VS Code, or Explorer")
        
        sync_btn = ctk.CTkButton(
            inner_btns,
            text="🔄 Sync",
            width=65,
            height=30,
            corner_radius=6,
            fg_color=("gray90", "#202924"),
            text_color=("#1D1D1F", "#ECF0ED"),
            hover_color=("gray80", "#2D362F"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda p=repo["path"]: self._update_repo(p)
        )
        sync_btn.pack(side="left", padx=3)
        ToolTip(sync_btn, "Update from GitHub and scan for changes")
        
        del_btn = ctk.CTkButton(
            inner_btns,
            text="✕",
            width=28,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            text_color="#FF3B30",
            hover_color=("#FFE5E5", "#3D2525"),
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=lambda p=repo["path"]: self._delete_repo(p)
        )
        del_btn.pack(side="left", padx=3)
        ToolTip(del_btn, "Remove project from local storage")

    def _show_readme_modal(self, repo):
        modal = ctk.CTkToplevel(self)
        modal.title(f"README: {repo['name']}")
        modal.geometry("900x700")
        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(1, weight=1)
        
        h = ctk.CTkFrame(modal, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        ctk.CTkLabel(h, text=f"📖 README: {repo['name']}", font=ctk.CTkFont(family="Inter", size=20, weight="bold")).pack(side="left")
        
        ctk.CTkButton(
            h,
            text="Open in Editor",
            width=110,
            height=32,
            corner_radius=8,
            command=lambda: self._open_repo(repo["path"])
        ).pack(side="right")
        
        tb = ctk.CTkTextbox(modal, font=ctk.CTkFont(family="Consolas", size=12), border_width=0,
                            fg_color=("#FFFFFF", "#1E2621"), text_color=("#1D1D1F", "#ECF0ED"))
        tb.grid(row=1, column=0, sticky="nsew", padx=25, pady=10)
        
        readme_content = self.repo_manager.get_repo_readme(repo["path"])
        if not readme_content:
            readme_content = "# No README Found\n\nThis repository does not have a standard README file (README.md, README.rst, README.txt)."
        
        tb.insert("1.0", readme_content)
        tb.configure(state="disabled")
        
        f = ctk.CTkFrame(modal, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 20))
        ctk.CTkButton(f, text="Dismiss", width=100, height=34, corner_radius=8, command=modal.destroy).pack(side="right")

    def _preview_remote_readme(self, repo):
        full_name = repo.get("full_name") or repo.get("name")
        modal = ctk.CTkToplevel(self)
        modal.title(f"Preview README: {full_name}")
        modal.geometry("900x700")
        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(1, weight=1)
        
        h = ctk.CTkFrame(modal, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        ctk.CTkLabel(h, text=f"📖 Remote Preview: {full_name}", font=ctk.CTkFont(family="Inter", size=20, weight="bold")).pack(side="left")
        
        status_lbl = ctk.CTkLabel(h, text="Fetching README...", font=ctk.CTkFont(size=12), text_color="gray")
        status_lbl.pack(side="left", padx=15)
        
        clone_btn = ctk.CTkButton(
            h,
            text="⚡ Clone Repository",
            width=130,
            height=32,
            corner_radius=8,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            command=lambda: [modal.destroy(), self._clone_from_search(repo)]
        )
        clone_btn.pack(side="right")
        
        tb = ctk.CTkTextbox(modal, font=ctk.CTkFont(family="Consolas", size=12), border_width=0,
                            fg_color=("#FFFFFF", "#1E2621"), text_color=("#1D1D1F", "#ECF0ED"))
        tb.grid(row=1, column=0, sticky="nsew", padx=25, pady=10)
        
        f = ctk.CTkFrame(modal, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 20))
        ctk.CTkButton(f, text="Dismiss", width=100, height=34, corner_radius=8, command=modal.destroy).pack(side="right")

        def fetch():
            content = self.github.get_remote_readme(full_name)
            if not content:
                content = f"# {full_name}\n\nNo README could be retrieved from GitHub API (or rate limit reached).\n\nDescription: {repo.get('description', 'N/A')}\n\nClick 'Clone Repository' to download the source code."
            self.after(0, lambda: self._populate_remote_readme(tb, status_lbl, content))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_remote_readme(self, tb, status_lbl, content):
        status_lbl.configure(text="✅ Loaded", text_color="#10B981")
        tb.delete("1.0", "end")
        tb.insert("1.0", content)
        tb.configure(state="disabled")

    def _show_file_tree_modal(self, repo):
        modal = ctk.CTkToplevel(self)
        modal.title(f"File Tree & Inspector: {repo['name']}")
        modal.geometry("950x750")
        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(1, weight=1)
        
        stats = self.repo_manager.get_repo_stats(repo["path"])
        h = ctk.CTkFrame(modal, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        
        title_box = ctk.CTkFrame(h, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text=f"🌳 Project Inspector: {repo['name']}", font=ctk.CTkFont(family="Inter", size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"Total files: {stats['file_count']}  |  Size: {stats['size_mb']} MB  |  Path: {repo['path']}", font=ctk.CTkFont(size=12), text_color=("gray50", "gray65")).pack(anchor="w")
        
        btn_box = ctk.CTkFrame(h, fg_color="transparent")
        btn_box.pack(side="right")
        
        ctk.CTkButton(
            btn_box,
            text="Launch Editor",
            width=110,
            height=32,
            corner_radius=8,
            command=lambda: self._open_repo(repo["path"])
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="Open Folder",
            width=100,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            command=lambda: self.repo_manager.open_in_explorer(repo["path"])
        ).pack(side="left", padx=4)
        
        # Dual-column split: Left = Tree, Right = Quick File Viewer
        split_frame = ctk.CTkFrame(modal, fg_color="transparent")
        split_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=5)
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)
        split_frame.grid_rowconfigure(0, weight=1)

        left_box = ctk.CTkFrame(split_frame, corner_radius=10, fg_color=("#FFFFFF", "#1E2621"))
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_box.grid_columnconfigure(0, weight=1)
        left_box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_box, text="Project Topology & Hierarchy", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 4))
        tree_txt = ctk.CTkTextbox(left_box, font=ctk.CTkFont(family="Consolas", size=11), border_width=0,
                                  fg_color="transparent", text_color=("#1D1D1F", "#ECF0ED"))
        tree_txt.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_lines = self.repo_manager.get_repo_file_tree(repo["path"])
        tree_txt.insert("1.0", "\n".join(tree_lines))
        tree_txt.configure(state="disabled")

        right_box = ctk.CTkFrame(split_frame, corner_radius=10, fg_color=("#FFFFFF", "#1E2621"))
        right_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_box.grid_columnconfigure(0, weight=1)
        right_box.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(right_box, text="Instant File Inspector", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 4))
        
        file_pick_row = ctk.CTkFrame(right_box, fg_color="transparent")
        file_pick_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        file_entry = ctk.CTkEntry(file_pick_row, placeholder_text="e.g. package.json or main.py", height=30)
        file_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        preview_txt = ctk.CTkTextbox(right_box, font=ctk.CTkFont(family="Consolas", size=11), border_width=0,
                                     fg_color=("#F5F7F3", "#151D18"), text_color=("#1D1D1F", "#ECF0ED"))
        preview_txt.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        preview_txt.insert("1.0", "# Enter any relative file path to view its contents directly.")

        def load_file():
            rel_path = file_entry.get().strip().lstrip("/\\")
            if not rel_path:
                return
            target_file = Path(repo["path"]) / rel_path
            if target_file.exists() and target_file.is_file():
                try:
                    content = target_file.read_text(encoding="utf-8", errors="ignore")[:25000]
                    preview_txt.delete("1.0", "end")
                    preview_txt.insert("1.0", content)
                except Exception as ex:
                    preview_txt.delete("1.0", "end")
                    preview_txt.insert("1.0", f"Error reading file: {ex}")
            else:
                preview_txt.delete("1.0", "end")
                preview_txt.insert("1.0", f"File '{rel_path}' not found in {repo['path']}.")

        file_entry.bind("<Return>", lambda e: load_file())
        ctk.CTkButton(file_pick_row, text="Inspect", width=70, height=30, command=load_file).pack(side="right")

        f = ctk.CTkFrame(modal, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", padx=25, pady=(10, 20))
        ctk.CTkButton(f, text="Dismiss", width=100, height=34, corner_radius=8, command=modal.destroy).pack(side="right")

    # ==========================================
    # 3. OSS LAUNCHPAD & CONTRIBUTOR SUITE
    # ==========================================
    def _create_learner_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["learner"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(25, 10))
        
        ctk.CTkLabel(
            header,
            text="🌱 OSS Launchpad & Contributor Suite",
            font=ctk.CTkFont(family="Inter", size=26, weight="bold")
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header,
            text="Everything you need to discover beginner-friendly issues, master open-source licenses, and make your first PR.",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=("gray50", "gray65")
        ).pack(anchor="w", pady=(2, 10))

        subtab_bar = ctk.CTkFrame(view, fg_color="transparent")
        subtab_bar.pack(fill="x", padx=25, pady=5)
        
        tabs = [
            ("issues", "🌟 Good First Issues"),
            ("licenses", "📜 License Decoder"),
            ("guide", "🚀 First PR & Git Guide")
        ]
        self.learner_tab_btns = {}
        self.learner_subviews = {}
        
        for key, label in tabs:
            btn = ctk.CTkButton(
                subtab_bar,
                text=label,
                height=34,
                corner_radius=8,
                fg_color=("#5E6C54", "#10B981") if key == "issues" else "transparent",
                text_color="white" if key == "issues" else ("gray20", "gray85"),
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                command=lambda k=key: self._switch_learner_tab(k)
            )
            btn.pack(side="left", padx=(0, 8))
            self.learner_tab_btns[key] = btn
            
        self.learner_container = ctk.CTkFrame(view, fg_color="transparent")
        self.learner_container.pack(fill="both", expand=True, padx=25, pady=10)
        
        self._build_good_first_issues_tab()
        self._build_license_decoder_tab()
        self._build_pr_guide_tab()
        
        self._switch_learner_tab("issues")

    def _switch_learner_tab(self, key):
        for name, subview in self.learner_subviews.items():
            if name == key:
                subview.pack(fill="both", expand=True)
            else:
                subview.pack_forget()
                
        for name, btn in self.learner_tab_btns.items():
            if name == key:
                btn.configure(fg_color=("#5E6C54", "#10B981"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "gray85"))

    def _build_good_first_issues_tab(self):
        frame = ctk.CTkFrame(self.learner_container, fg_color="transparent")
        self.learner_subviews["issues"] = frame
        
        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(ctrl, text="Filter Language:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.learner_lang_filter = ctk.CTkComboBox(
            ctrl,
            values=["All", "Python", "TypeScript", "JavaScript", "Rust", "Go"],
            width=130
        )
        self.learner_lang_filter.set("All")
        self.learner_lang_filter.pack(side="left")
        
        ctk.CTkButton(
            ctrl,
            text="Find Beginner Opportunities",
            width=190,
            height=32,
            corner_radius=8,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self._load_good_first_issues
        ).pack(side="left", padx=10)
        
        self.issues_list_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.issues_list_frame.pack(fill="both", expand=True)
        
        self._load_good_first_issues()

    def _load_good_first_issues(self):
        for w in self.issues_list_frame.winfo_children():
            w.destroy()
            
        ctk.CTkLabel(self.issues_list_frame, text="Searching for beginner-friendly repositories...", text_color="gray").pack(pady=20)
        lang = getattr(self, "learner_lang_filter", None)
        selected_lang = lang.get() if lang else "All"
        
        def run():
            results = self.github.search_good_first_issues(language=selected_lang)
            self.after(0, lambda: self._display_good_first_issues(results))
            
        threading.Thread(target=run, daemon=True).start()

    def _display_good_first_issues(self, repos):
        for w in self.issues_list_frame.winfo_children():
            w.destroy()
            
        if not repos:
            ctk.CTkLabel(self.issues_list_frame, text="No repositories found.", text_color="gray").pack(pady=20)
            return
            
        for repo in repos:
            card = ctk.CTkFrame(self.issues_list_frame, height=110, corner_radius=12, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
            card.pack(fill="x", pady=6)
            card.grid_propagate(False)
            
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=20, pady=12)
            
            t = ctk.CTkFrame(info, fg_color="transparent")
            t.pack(fill="x")
            
            ctk.CTkLabel(t, text=repo["full_name"], font=ctk.CTkFont(family="Inter", size=16, weight="bold")).pack(side="left")
            ctk.CTkLabel(t, text=f"  ● {repo.get('language', 'Polyglot')}  |  ★ {repo.get('stargazers_count', 0):,}", font=ctk.CTkFont(size=11), text_color=config.COLORS["dark"]["accent"]).pack(side="left", padx=8)
            
            gfi_badge = ctk.CTkLabel(
                t,
                text=" 🌟 Good First Issues Available ",
                font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                fg_color=("#E8EDE6", "#1D2620"),
                text_color=("#10B981", "#34D399"),
                corner_radius=4
            )
            gfi_badge.pack(side="left", padx=5)
            
            desc = repo.get("description", "") or "No description provided."
            ctk.CTkLabel(info, text=desc[:120] + ("..." if len(desc) > 120 else ""), font=ctk.CTkFont(size=11), text_color=("gray40", "gray70"), anchor="w").pack(fill="x", pady=(2, 0))
            
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", fill="y", padx=15)
            
            top_btns = ctk.CTkFrame(actions, fg_color="transparent")
            top_btns.pack(side="top", pady=(14, 4))

            ctk.CTkButton(
                top_btns,
                text="👁️ Readme",
                width=75,
                height=30,
                corner_radius=6,
                fg_color="transparent",
                border_width=1,
                border_color=("#5E6C54", "#10B981"),
                text_color=("#5E6C54", "#10B981"),
                font=ctk.CTkFont(size=11),
                command=lambda r=repo: self._preview_remote_readme(r)
            ).pack(side="left", padx=3)

            ctk.CTkButton(
                top_btns,
                text="Issues on GitHub",
                width=110,
                height=30,
                corner_radius=6,
                command=lambda u=f"{repo.get('html_url')}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22": webbrowser.open(u)
            ).pack(side="left", padx=3)
            
            ctk.CTkButton(
                actions,
                text="Clone & Setup",
                width=190,
                height=32,
                corner_radius=8,
                fg_color=("#5E6C54", "#10B981"),
                hover_color=("#4F5B46", "#059669"),
                text_color="white",
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(side="top")

    def _build_license_decoder_tab(self):
        frame = ctk.CTkFrame(self.learner_container, fg_color="transparent")
        self.learner_subviews["licenses"] = frame
        
        ctk.CTkLabel(
            frame,
            text="Interactive Open-Source License Decoder",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 6))
        
        ctk.CTkLabel(
            frame,
            text="Select any license to inspect permissions, commercial rights, patent grants, and copyleft obligations.",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray65")
        ).pack(anchor="w", pady=(0, 15))
        
        btn_bar = ctk.CTkFrame(frame, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(0, 10))
        
        self.license_detail_box = ctk.CTkFrame(frame, corner_radius=12, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
        self.license_detail_box.pack(fill="x", pady=5)
        
        kb = self.github.get_license_knowledge_base()
        for lic_key in kb.keys():
            ctk.CTkButton(
                btn_bar,
                text=lic_key,
                width=100,
                height=32,
                corner_radius=8,
                fg_color=("gray90", "#202924"),
                text_color=("#1D1D1F", "#ECF0ED"),
                command=lambda k=lic_key: self._display_license_info(k)
            ).pack(side="left", padx=(0, 8))
            
        self._display_license_info("MIT")

        # Quick Decision Guide
        quiz_box = ctk.CTkFrame(frame, corner_radius=12, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
        quiz_box.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(quiz_box, text="🎯 What License Should I Choose for My Project?", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=("#2C342C", "#10B981")).pack(anchor="w", padx=20, pady=(12, 6))

        quiz_rules = [
            ("I want maximum adoption with zero restrictions:", "Choose MIT (Short, simple, permissive)"),
            ("I want commercial protection with explicit patent rights:", "Choose Apache 2.0 (Industry standard for APIs & enterprise)"),
            ("I want academic/scientific use and prohibit name endorsement:", "Choose BSD-3-Clause (Protects author credentials)"),
            ("I want all derivative works to remain permanently open source:", "Choose GPL v3 (Strong copyleft)"),
            ("I am building a SaaS / cloud backend service that must stay open:", "Choose AGPL v3 (Network copyleft)"),
            ("I want to dedicate my code entirely to the public domain:", "Choose The Unlicense / CC0")
        ]
        for q, a in quiz_rules:
            r = ctk.CTkFrame(quiz_box, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(r, text=f"• {q}", font=ctk.CTkFont(size=11, weight="bold"), width=360, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=f"➜ {a}", font=ctk.CTkFont(size=11), text_color=config.COLORS["dark"]["accent"], anchor="w").pack(side="left")
        ctk.CTkLabel(quiz_box, text="", height=6).pack()

    def _display_license_info(self, lic_key):
        for w in self.license_detail_box.winfo_children():
            w.destroy()
            
        kb = self.github.get_license_knowledge_base()
        data = kb.get(lic_key, kb["MIT"])
        
        pad = ctk.CTkFrame(self.license_detail_box, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=25, pady=20)
        
        top = ctk.CTkFrame(pad, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(top, text=data["name"], font=ctk.CTkFont(family="Inter", size=20, weight="bold")).pack(side="left")
        
        badge_col = "#10B981" if not data.get("copyleft") else "#F59E0B"
        ctk.CTkLabel(
            top,
            text=f"  {data['badge']}  ",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=("#E8EDE6", "#1D2620"),
            text_color=badge_col,
            corner_radius=4
        ).pack(side="left", padx=12)
        
        ctk.CTkLabel(pad, text="Plain-English Summary:", font=ctk.CTkFont(family="Inter", size=13, weight="bold")).pack(anchor="w", pady=(10, 2))
        ctk.CTkLabel(pad, text=data["summary"], font=ctk.CTkFont(size=12), wraplength=700, justify="left", text_color=("gray30", "gray80")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(pad, text="Core Obligations:", font=ctk.CTkFont(family="Inter", size=13, weight="bold")).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(pad, text=f"• {data['obligations']}", font=ctk.CTkFont(size=12), wraplength=700, justify="left", text_color=("gray30", "gray80")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(pad, text="Recommended Use Case:", font=ctk.CTkFont(family="Inter", size=13, weight="bold")).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(pad, text=f"• {data['ideal_for']}", font=ctk.CTkFont(size=12), wraplength=700, justify="left", text_color=config.COLORS["dark"]["accent"]).pack(anchor="w")

    def _build_pr_guide_tab(self):
        frame = ctk.CTkFrame(self.learner_container, fg_color="transparent")
        self.learner_subviews["guide"] = frame
        
        top_bar = ctk.CTkFrame(frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            top_bar,
            text="🚀 First Pull Request Workflow & Git Cheatsheet",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold")
        ).pack(side="left")

        self.pr_progress_label = ctk.CTkLabel(
            top_bar,
            text="Progress: 0/20 Steps Completed (0%)",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=config.COLORS["dark"]["accent"]
        )
        self.pr_progress_label.pack(side="right")

        self.pr_checkboxes = []

        for item in FIRST_PR_WORKFLOW:
            card = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
            card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(card, text=item["phase"], font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=("#2C342C", "#10B981")).pack(anchor="w", padx=15, pady=(10, 4))
            for step in item["steps"]:
                cb = ctk.CTkCheckBox(
                    card,
                    text=f" {step}",
                    font=ctk.CTkFont(size=11),
                    text_color=("gray30", "gray80"),
                    command=self._update_pr_progress
                )
                cb.pack(anchor="w", padx=15, pady=3)
                self.pr_checkboxes.append(cb)
            ctk.CTkLabel(card, text="", height=4).pack()

        git_box = ctk.CTkFrame(frame, corner_radius=10, fg_color=("#FFFFFF", "#151D18"), border_width=1, border_color=("#D1D9CD", "#202924"))
        git_box.pack(fill="x", pady=10)
        
        ctk.CTkLabel(git_box, text="⚡ Essential Git Commands", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=("#2C342C", "#10B981")).pack(anchor="w", padx=15, pady=(10, 6))
        for g in GIT_ESSENTIALS[:6]:
            row = ctk.CTkFrame(git_box, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(row, text=g["command"], font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), width=240, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"- {g['description']}", font=ctk.CTkFont(size=11), text_color=("gray40", "gray70"), anchor="w").pack(side="left")
        ctk.CTkLabel(git_box, text="", height=6).pack()

    def _update_pr_progress(self):
        total = len(self.pr_checkboxes)
        if total == 0:
            return
        checked = sum(1 for cb in self.pr_checkboxes if cb.get() == 1)
        pct = int((checked / total) * 100)
        self.pr_progress_label.configure(text=f"Progress: {checked}/{total} Steps Completed ({pct}%)")

    # ==========================================
    # 4. TRENDING VIEW
    # ==========================================
    def _create_trending_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["trending"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            header,
            text="GitHub Trending",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")
        
        ctk.CTkButton(
            header,
            text="Open in Browser",
            width=140,
            height=36,
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            border_color=("#5E6C54", "#10B981"),
            text_color=("#5E6C54", "#10B981"),
            font=ctk.CTkFont(family="Inter", weight="bold"),
            command=lambda: webbrowser.open("https://github.com/trending/")
        ).pack(side="right")
        
        ctk.CTkButton(
            header,
            text="Refresh",
            width=100,
            height=36,
            corner_radius=10,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", weight="bold"),
            command=self._load_trending
        ).pack(side="right", padx=10)
        
        filter_frame = ctk.CTkFrame(view, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(filter_frame, text="Language:").pack(side="left", padx=5)
        
        self.trending_lang = ctk.CTkComboBox(
            filter_frame,
            values=["All", "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#"],
            command=lambda x: self._load_trending()
        )
        self.trending_lang.set("All")
        self.trending_lang.pack(side="left", padx=5)
        
        self.trending_list = ctk.CTkFrame(view, fg_color="transparent")
        self.trending_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._load_trending()

    def _load_trending(self):
        for widget in self.trending_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.trending_list,
            text="Loading trending repos...",
            text_color="gray"
        ).pack(pady=20)
        
        lang = self.trending_lang.get()
        language = "" if lang == "All" else lang
        
        def load():
            try:
                repos = self.github.search_trending_repos(language=language)
                self.after(0, lambda: self._display_trending(repos))
            except Exception as err:
                err_msg = str(err)
                self.after(0, lambda m=err_msg: self._trending_error(m))
        
        threading.Thread(target=load, daemon=True).start()

    def _display_trending(self, repos):
        for widget in self.trending_list.winfo_children():
            widget.destroy()
        
        self.trending_repos = repos
        
        if not repos:
            ctk.CTkLabel(
                self.trending_list,
                text="No trending repos found",
                text_color="gray"
            ).pack(pady=40)
            return
        
        for repo in repos:
            card = ctk.CTkFrame(self.trending_list, height=140, corner_radius=12)
            card.pack(fill="x", pady=8, padx=5)
            card.grid_propagate(False)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)
            
            ctk.CTkLabel(
                info_frame,
                text=repo['full_name'],
                font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
                anchor="w"
            ).pack(fill="x")
            
            desc = repo.get("description", "No description provided.")
            ctk.CTkLabel(
                info_frame,
                text=desc[:120] + "..." if len(desc) > 120 else desc,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=("gray40", "gray70"),
                anchor="w",
                justify="left",
                wraplength=600
            ).pack(fill="x", pady=5)
            
            stats_text = f"★ {repo.get('stargazers_count', 0)}   ⑂ {repo.get('forks_count', 0)}"
            if repo.get("language"):
                stats_text += f"   ● {repo['language']}"
            if repo.get("license"):
                stats_text += f"   ⚖️ {repo['license']}"
            
            ctk.CTkLabel(
                info_frame,
                text=stats_text,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=config.COLORS["dark"]["accent"],
                anchor="w"
            ).pack(fill="x")
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            btn_frame.pack(side="right", fill="y", padx=20)
            
            inner_action = ctk.CTkFrame(btn_frame, fg_color="transparent")
            inner_action.pack(expand=True)

            ctk.CTkButton(
                inner_action,
                text="👁️ Readme",
                width=80,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                border_width=1,
                border_color=("#5E6C54", "#10B981"),
                text_color=("#5E6C54", "#10B981"),
                font=ctk.CTkFont(family="Inter", size=11),
                command=lambda r=repo: self._preview_remote_readme(r)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                inner_action,
                text="Clone",
                width=80,
                height=32,
                corner_radius=8,
                fg_color=("#5E6C54", "#10B981"),
                hover_color=("#4F5B46", "#059669"),
                text_color="white",
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(side="left", padx=4)

    def _trending_error(self, error):
        for widget in self.trending_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.trending_list,
            text=f"Notice: {error} (Check connection)",
            text_color="#ff4757"
        ).pack(pady=20)

    # ==========================================
    # 5. SEARCH VIEW
    # ==========================================
    def _create_search_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["search"] = view
        
        ctk.CTkLabel(
            view,
            text="Search GitHub Repositories",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        search_frame = ctk.CTkFrame(view, fg_color="transparent", border_width=0)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Find repositories across 50M+ open source projects...",
            height=44,
            corner_radius=10
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._search_repos())
        
        ctk.CTkButton(
            search_frame,
            text="Search",
            width=110,
            height=44,
            corner_radius=12,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            command=self._search_repos
        ).pack(side="right")
        
        lang_frame = ctk.CTkFrame(view, fg_color="transparent")
        lang_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(lang_frame, text="Language:").pack(side="left", padx=5)
        
        self.search_lang = ctk.CTkComboBox(
            lang_frame,
            values=["", "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#"]
        )
        self.search_lang.pack(side="left", padx=5)
        
        self.search_results_list = ctk.CTkFrame(view, fg_color="transparent")
        self.search_results_list.pack(fill="both", expand=True, padx=20, pady=10)

    def _search_repos(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        
        for widget in self.search_results_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.search_results_list,
            text="Searching...",
            text_color="gray"
        ).pack(pady=20)
        
        lang = self.search_lang.get()
        
        def search():
            try:
                repos = self.github.search_repos(query, language=lang if lang else None)
                self.after(0, lambda: self._display_search_results(repos))
            except Exception as err:
                err_msg = str(err)
                self.after(0, lambda m=err_msg: self._search_error(m))
        
        threading.Thread(target=search, daemon=True).start()

    def _display_search_results(self, repos):
        for widget in self.search_results_list.winfo_children():
            widget.destroy()
        
        self.search_results = repos
        
        if not repos:
            ctk.CTkLabel(
                self.search_results_list,
                text="No results found",
                text_color="gray"
            ).pack(pady=40)
            return
        
        for repo in repos:
            card = ctk.CTkFrame(self.search_results_list, height=140, corner_radius=12)
            card.pack(fill="x", pady=8, padx=5)
            card.grid_propagate(False)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)
            
            ctk.CTkLabel(
                info_frame,
                text=repo['full_name'],
                font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
                anchor="w"
            ).pack(fill="x")
            
            desc = repo.get("description", "No description provided.")
            ctk.CTkLabel(
                info_frame,
                text=desc[:120] + "..." if len(desc) > 120 else desc,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=("gray40", "gray70"),
                anchor="w",
                justify="left",
                wraplength=600
            ).pack(fill="x", pady=5)
            
            stats_text = f"★ {repo.get('stargazers_count', 0)}   ⑂ {repo.get('forks_count', 0)}"
            if repo.get("language"):
                stats_text += f"   ● {repo['language']}"
            
            ctk.CTkLabel(
                info_frame,
                text=stats_text,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=config.COLORS["dark"]["accent"],
                anchor="w"
            ).pack(fill="x")
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            btn_frame.pack(side="right", fill="y", padx=20)
            
            inner_action = ctk.CTkFrame(btn_frame, fg_color="transparent")
            inner_action.pack(expand=True)

            ctk.CTkButton(
                inner_action,
                text="👁️ Readme",
                width=80,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                border_width=1,
                border_color=("#5E6C54", "#10B981"),
                text_color=("#5E6C54", "#10B981"),
                font=ctk.CTkFont(family="Inter", size=11),
                command=lambda r=repo: self._preview_remote_readme(r)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                inner_action,
                text="Clone",
                width=80,
                height=32,
                corner_radius=8,
                fg_color=("#5E6C54", "#10B981"),
                hover_color=("#4F5B46", "#059669"),
                text_color="white",
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(side="left", padx=4)

    def _search_error(self, error):
        for widget in self.search_results_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.search_results_list,
            text=f"Notice: {error}",
            text_color="#ff4757"
        ).pack(pady=20)

    def _clone_from_search(self, repo):
        url = repo.get("clone_url") or f"https://github.com/{repo['full_name']}.git"
        lic = repo.get("license_spdx_id")
        result = self.repo_manager.add_repo(url, license_spdx=lic)
        
        if result.get("status") == "cloned":
            messagebox.showinfo("Success", f"Cloned {result['name']} into {result.get('folder', 'License')} folder!")
            self._load_repos()
        elif result.get("status") == "already_exists":
            messagebox.showinfo("Info", "Repository already exists in your local library!")
        else:
            messagebox.showerror("Error", result.get("error", "Failed to clone"))

    # ==========================================
    # 6. ADD REPOSITORY VIEW
    # ==========================================
    def _create_add_view(self):
        view = ctk.CTkFrame(self.content, fg_color="transparent")
        self.views["add"] = view
        
        ctk.CTkLabel(
            view,
            text="Add Repository",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold")
        ).pack(pady=(40, 10))
        
        ctk.CTkLabel(
            view,
            text="Import any GitHub repository by URL or owner/name (e.g. facebook/react)",
            text_color=("gray50", "gray60")
        ).pack(pady=5)
        
        self.repo_url_entry = ctk.CTkEntry(
            view,
            placeholder_text="e.g. tiangolo/fastapi or https://github.com/pallets/flask",
            width=500,
            height=48,
            corner_radius=12
        )
        self.repo_url_entry.pack(pady=30)
        
        ctk.CTkButton(
            view,
            text="Clone Repository",
            width=240,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(weight="bold"),
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            command=self._add_repo
        ).pack(pady=10)
        
        self.add_status = ctk.CTkLabel(view, text="", font=ctk.CTkFont(size=13))
        self.add_status.pack(pady=20)

    def _add_repo(self):
        url = self.repo_url_entry.get().strip()
        if not url:
            self.add_status.configure(text="Please enter a repository URL or owner/repo")
            return
        
        self.add_status.configure(text="Cloning repository into categorized license folder...")
        
        def clone():
            result = self.repo_manager.add_repo(url)
            self.after(0, lambda: self._add_repo_result(result))
        
        threading.Thread(target=clone, daemon=True).start()

    def _add_repo_result(self, result):
        if result.get("status") == "cloned":
            self.add_status.configure(text=f"Success! Cloned {result['name']} into {result.get('folder', 'License')} folder")
            self.repo_url_entry.delete(0, "end")
            self._load_repos()
        elif result.get("status") == "already_exists":
            self.add_status.configure(text=result.get("message", "Already exists"))
        else:
            self.add_status.configure(text=f"Error: {result.get('error', 'Unknown error')}")

    # ==========================================
    # 7. AI EXPLAIN & ORACLE VIEW
    # ==========================================
    def _create_ai_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["ai"] = view
        
        ctk.CTkLabel(
            view,
            text="Analysis Agent & Project Oracle",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold")
        ).pack(anchor="w", padx=20, pady=(30, 10))
        
        model_frame = ctk.CTkFrame(view, fg_color="transparent", border_width=0)
        model_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(model_frame, text="Intelligence Engine:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        self.model_selector = ctk.CTkComboBox(
            model_frame,
            values=config.OLLAMA_MODELS,
            height=36,
            corner_radius=8,
            command=self._change_model
        )
        self.model_selector.set(config.OLLAMA_DEFAULT_MODEL)
        self.model_selector.pack(side="left", fill="x", expand=True)

        self.refresh_models_btn = ctk.CTkButton(
            model_frame,
            text="🔄",
            width=36,
            height=36,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("#D1D5CB", "#202924"),
            text_color=("#5E6C54", "#10B981"),
            command=self._refresh_models
        )
        self.refresh_models_btn.pack(side="left", padx=5)
        
        self.ollama_status = ctk.CTkLabel(model_frame, text="Checking status...", font=ctk.CTkFont(size=12))
        self.ollama_status.pack(side="right", padx=10)
        
        threading.Thread(target=self._check_ollama, daemon=True).start()
        
        input_frame = ctk.CTkFrame(view, corner_radius=12)
        input_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tpl_bar = ctk.CTkFrame(input_frame, fg_color="transparent")
        tpl_bar.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(tpl_bar, text="Quick Prompt Starters:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 8))

        starters = [
            ("🏛️ Architecture Review", "Analyze the system architecture of this code, identify patterns, and evaluate scalability:"),
            ("🔒 Security & Debt Scan", "Audit this code for security vulnerabilities, concurrency bugs, and technical debt:"),
            ("🌱 Beginner Explainer", "Explain this code step-by-step for a beginner software developer:"),
            ("🤝 Contributor Guide", "How can an open source contributor add unit tests and refactor this code:")
        ]
        for lbl, prompt_text in starters:
            ctk.CTkButton(
                tpl_bar,
                text=lbl,
                height=26,
                corner_radius=6,
                fg_color=("gray90", "#202924"),
                text_color=("#1D1D1F", "#ECF0ED"),
                font=ctk.CTkFont(size=10),
                command=lambda p=prompt_text: self._apply_prompt_template(p)
            ).pack(side="left", padx=3)
        
        self.code_input = ctk.CTkTextbox(input_frame, height=200, border_width=0,
                                          fg_color=("#FFFFFF", "#1E2621"),
                                          text_color=("#1D1D1F", "#ECF0ED"))
        self.code_input.pack(fill="x", padx=20, pady=5)
        
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent", border_width=0)
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        self.run_agent_btn = ctk.CTkButton(
            btn_frame,
            text="Run Analysis Agent",
            height=40,
            corner_radius=12,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", weight="bold"),
            command=self._explain_code
        )
        self.run_agent_btn.pack(side="left")
        
        ctk.CTkButton(
            btn_frame,
            text="Clear",
            width=80,
            height=40,
            corner_radius=12,
            fg_color="transparent",
            border_width=1,
            border_color=("#5E6C54", "#10B981"),
            text_color=("#5E6C54", "#10B981"),
            command=self._clear_ai
        ).pack(side="right")
        
        self.ai_response_frame = ctk.CTkFrame(view, corner_radius=12)
        self.ai_response_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            self.ai_response_frame, 
            text="Agent Intelligence Output",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        self.ai_response = ctk.CTkTextbox(self.ai_response_frame, height=300, border_width=0,
                                           fg_color=("#FFFFFF", "#151D18"),
                                           text_color=("#1D1D1F", "#ECF0ED"))
        self.ai_response.pack(fill="both", expand=True, padx=20, pady=5)
        
        ctk.CTkButton(
            self.ai_response_frame,
            text="Copy Analysis",
            height=40,
            corner_radius=12,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", weight="bold"),
            command=self._copy_response
        ).pack(pady=20)

    def _apply_prompt_template(self, template_text):
        current = self.code_input.get("1.0", "end").strip()
        self.code_input.delete("1.0", "end")
        if current:
            self.code_input.insert("1.0", f"{template_text}\n\n{current}")
        else:
            self.code_input.insert("1.0", f"{template_text}\n\n# Paste your code or architectural snippet below:")

    # ==========================================
    # 8. SETTINGS VIEW
    # ==========================================
    def _create_settings_view(self):
        view = ctk.CTkFrame(self.content, fg_color="transparent")
        self.views["settings"] = view
        
        ctk.CTkLabel(
            view,
            text="Settings",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold")
        ).pack(anchor="w", padx=30, pady=(40, 20))
        
        # Section: Storage
        storage_frame = ctk.CTkFrame(view, corner_radius=12)
        storage_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(
            storage_frame,
            text="Local Storage",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(
            storage_frame,
            text=str(self.repo_manager.get_repos_path()),
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(0, 15))
        
        ctk.CTkButton(
            storage_frame,
            text="Reveal in Explorer",
            height=32,
            corner_radius=8,
            fg_color=("gray90", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray80", "gray35"),
            command=self._open_repos_folder
        ).pack(anchor="w", padx=20, pady=(0, 20))

        # Section: GitHub Authentication
        auth_frame = ctk.CTkFrame(view, corner_radius=12)
        auth_frame.pack(fill="x", padx=30, pady=10)

        ctk.CTkLabel(
            auth_frame,
            text="GitHub Authentication",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        rate = self.github.get_rate_limit_status()
        auth_status = "Authenticated" if rate.get("authenticated") else "Unauthenticated (60 req/hr)"
        ctk.CTkLabel(auth_frame, text=f"Status: {auth_status} - Quota: {rate.get('remaining')}/{rate.get('limit')}", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20)

        ctk.CTkButton(
            auth_frame,
            text="Configure Personal Access Token",
            height=32,
            corner_radius=8,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            command=self._prompt_github_token
        ).pack(anchor="w", padx=20, pady=(10, 20))
        
        # Section: Ollama
        ollama_frame = ctk.CTkFrame(view, corner_radius=12)
        ollama_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(
            ollama_frame,
            text="Ollama Engine",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(ollama_frame, text="Endpoint URL", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20)
        
        self.ollama_url_entry = ctk.CTkEntry(ollama_frame, width=400, height=36, corner_radius=8)
        self.ollama_url_entry.insert(0, self.ollama.base_url)
        self.ollama_url_entry.pack(anchor="w", padx=20, pady=10)
        
        ctk.CTkButton(
            ollama_frame,
            text="Save Configuration",
            height=36,
            corner_radius=8,
            command=self._save_ollama_url
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def _show_view(self, view_name):
        for view in self.views.values():
            view.grid_forget()
        
        view = self.views[view_name]
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _switch_view(self, view_name):
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()
        
        self._show_view(view_name)
        
        for key, btn in self.nav_buttons.items():
            if key == view_name:
                btn.configure(
                    fg_color=("#5E6C54", "#10B981"), 
                    text_color="white",
                    hover_color=("#4F5B46", "#059669")
                )
            else:
                btn.configure(
                    fg_color="transparent", 
                    text_color=("gray20", "gray85"),
                    hover_color=("gray90", "#1D2620")
                )

    def _update_repo(self, path):
        def update():
            try:
                result = self.repo_manager.update_repo(path)
                if result.get("status") == "updated":
                    self.after(0, lambda: messagebox.showinfo("Success", "Repository updated!"))
                else:
                    err = result.get("error", "Update failed")
                    self.after(0, lambda m=err: messagebox.showerror("Error", m))
                self.after(0, self._load_repos)
            except Exception as e:
                self.after(0, lambda m=str(e): messagebox.showerror("Error", m))
        
        threading.Thread(target=update, daemon=True).start()

    def _run_architecture_audit(self, repo):
        audit_win = ctk.CTkToplevel(self)
        audit_win.title(f"Oracle Audit: {repo['name']}")
        audit_win.geometry("900x750")
        audit_win.grid_columnconfigure(0, weight=1)
        audit_win.grid_rowconfigure(2, weight=1)
        
        header = ctk.CTkFrame(audit_win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 10))
        
        title_lbl = ctk.CTkLabel(header, text=f"🏛️ Architectural Audit: {repo['name']}", 
                                font=ctk.CTkFont(family="Inter", size=24, weight="bold"))
        title_lbl.pack(side="left")
        
        progress_frame = ctk.CTkFrame(audit_win, height=44, fg_color=("#E8EDE6", "#1D2620"))
        progress_frame.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        status_label = ctk.CTkLabel(progress_frame, text="⚙️ Initializing Project Oracle...",
                                   font=ctk.CTkFont(family="Inter", size=13))
        status_label.pack(pady=8, padx=20, side="left")
        
        output_txt = ctk.CTkTextbox(audit_win, font=ctk.CTkFont(family="Consolas", size=13),
                                   fg_color=("#FFFFFF", "#1E2621"), 
                                   text_color=("#1D1D1F", "#ECF0ED"),
                                   border_width=0)
        output_txt.grid(row=2, column=0, sticky="nsew", padx=40, pady=10)
        
        footer = ctk.CTkFrame(audit_win, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=40, pady=(10, 40))
        
        close_btn = ctk.CTkButton(footer, text="Dismiss", width=120, height=36,
                                 fg_color=("#5E6C54", "#10B981"),
                                 hover_color=("#4F5B46", "#059669"),
                                 text_color="white",
                                 command=audit_win.destroy)
        close_btn.pack(side="right")

        def run():
            try:
                self.after(0, lambda: status_label.configure(text="🔍 Deep Scanning Repository Structure..."))
                context = self.repo_manager.get_project_context(repo["path"])
                if not context or not context.get("file_tree"):
                    raise Exception("No project files found. Is the repository empty?")
                
                self.after(0, lambda: status_label.configure(text="🧠 Reasoning through Project Architecture..."))
                audit = self.ollama.perform_architectural_audit(context)
                if not audit:
                    raise Exception("AI failed to generate an audit report.")
                
                self.after(0, lambda: status_label.configure(text="🏷️ Generating Semantic Smart Tags..."))
                readme = self.repo_manager.get_repo_readme(repo["path"])
                tags = self.ollama.suggest_smart_tags(readme, context)
                
                self.after(0, lambda: status_label.configure(text="💾 Persisting insights to Knowledge Base..."))
                from database import get_database
                db = get_database()
                
                search_names = [
                    repo["name"].replace("_", "/", 1),
                    repo["name"],
                    Path(repo["path"]).name.replace("_", "/", 1)
                ]
                
                db_repo = None
                for n in search_names:
                    db_repo = db.get_repository(full_name=n)
                    if db_repo: break
                
                if db_repo:
                    db_repo.architectural_audit = audit
                    db_repo.smart_tags = tags
                    db.save_repository(db_repo)
                
                self.after(0, lambda a=audit: self._show_audit_results(output_txt, status_label, a))
                self.after(0, self._load_repos)
                
            except Exception as e:
                self.after(0, lambda m=str(e): status_label.configure(text=f"❌ Error: {m}"))
                logger.error(f"Audit error for {repo['name']}: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _show_audit_results(self, txt_widget, label_widget, content):
        label_widget.configure(text="✅ Project Oracle: Audit Complete")
        txt_widget.insert("1.0", content)
        txt_widget.configure(state="disabled")
        self._load_repos()

    def _update_all_repos(self):
        def update():
            try:
                results = self.repo_manager.update_all_repos()
                success = sum(1 for r in results if r.get("status") == "updated")
                self.after(0, lambda: messagebox.showinfo("Update Complete", f"Updated {success} of {len(results)} repositories"))
                self.after(0, self._load_repos)
            except Exception as e:
                self.after(0, lambda m=str(e): messagebox.showerror("Error", m))
        
        threading.Thread(target=update, daemon=True).start()

    def _delete_repo(self, path):
        if messagebox.askyesno("Delete", "Are you sure you want to delete this repository?"):
            result = self.repo_manager.delete_repo(path)
            if result.get("status") == "deleted":
                messagebox.showinfo("Success", "Repository deleted!")
                self._load_repos()
            else:
                messagebox.showerror("Error", result.get("error", "Delete failed"))

    def _open_repo(self, path):
        self.repo_manager.open_in_editor(path)

    def _open_in_explorer(self, path):
        self.repo_manager.open_in_explorer(path)

    def _open_repos_folder(self):
        try:
            self.repo_manager.open_folder()
        except Exception as e:
            logger.error(f"Error opening folder: {e}")

    def _refresh_models(self):
        self.ollama_status.configure(text="Refreshing...", text_color=("gray20", "gray80"))
        threading.Thread(target=self._check_ollama, daemon=True).start()

    def _check_ollama(self):
        available = self.ollama.is_available()
        models = []
        if available:
            models = self.ollama.get_available_models()
        
        def update_ui():
            self.ollama_status.configure(
                text="Connected" if available else "Heuristic Fallback",
                text_color="#10B981" if available else "#F59E0B"
            )
            if available and models:
                current = self.model_selector.get()
                self.model_selector.configure(values=models)
                if current in models:
                    self.model_selector.set(current)
                elif config.OLLAMA_DEFAULT_MODEL in models:
                    self.model_selector.set(config.OLLAMA_DEFAULT_MODEL)
                else:
                    self.model_selector.set(models[0])
                    self.ollama.set_model(models[0])
        
        self.after(0, update_ui)

    def _change_model(self, model):
        self.ollama.set_model(model)

    def _explain_code(self):
        code = self.code_input.get("1.0", "end").strip()
        if not code:
            messagebox.showwarning("Warning", "Please enter some code")
            return
        
        self.ai_response.delete("1.0", "end")
        self.ai_response.insert("1.0", "⚙️ Analysis Agent starting...\n[1/3] Mapping architecture...\n[2/3] Tracing logic flows...\n[3/3] Scanning for optimizations...")
        self.run_agent_btn.configure(state="disabled")
        
        def run():
            try:
                response = self.ollama.run_analysis_agent(code)
                self.after(0, lambda: self._show_ai_response(response))
            except Exception as e:
                self.after(0, lambda e=e: self._show_ai_response(f"Agent Error: {e}"))
            finally:
                self.after(0, lambda: self.run_agent_btn.configure(state="normal"))
        
        threading.Thread(target=run, daemon=True).start()

    def _show_ai_response(self, response):
        self.ai_response.delete("1.0", "end")
        self.ai_response.insert("1.0", response)

    def _clear_ai(self):
        self.code_input.delete("1.0", "end")
        self.ai_response.delete("1.0", "end")

    def _copy_response(self):
        response = self.ai_response.get("1.0", "end").strip()
        if response:
            self.clipboard_clear()
            self.clipboard_append(response)
            messagebox.showinfo("Copied", "Response copied!")

    def _save_ollama_url(self):
        self.ollama.base_url = self.ollama_url_entry.get()
        threading.Thread(target=self._check_ollama, daemon=True).start()
        messagebox.showinfo("Saved", "Ollama URL updated!")


def main():
    app = RepoGrabberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
