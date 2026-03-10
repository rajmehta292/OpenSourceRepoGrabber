"""
OpenSource Repo Grabber - Complete GUI with Trending & Search
"""
import os
import threading
import logging
import webbrowser

import customtkinter as ctk
from tkinter import messagebox, filedialog

import config
from repo_manager import get_repo_manager
from ollama_client import get_ollama_client
from github_api import get_github_client

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
        self._is_active = True # Protection against delayed shows

    @classmethod
    def get_instance(cls, root=None):
        if cls._instance is None and root is not None:
            cls._instance = cls(root)
        return cls._instance

    def show(self, widget, text):
        if not text:
            self.hide()
            return
            
        # If already showing for the same widget, do nothing
        if self.active_widget == widget and self.is_shown:
            return

        # Cancel any pending show
        self._cancel_pending()
        self._is_active = True
        
        # Debounce: Wait 250ms before showing
        self.show_id = self.root.after(250, lambda: self._actual_show(widget, text))

    def _actual_show(self, widget, text):
        if not self._is_active: return
        self.hide()
        
        # Absolute exclusivity check
        self._is_active = True
        self.active_widget = widget
        
        # Calculate position: To the right of the button for sidebar
        # winfo_rootx + winfo_width + 10
        x = widget.winfo_rootx() + widget.winfo_width() + 10
        y = widget.winfo_rooty() + (widget.winfo_height() // 4)
        
        try:
            self.tip_window = tw = ctk.CTkToplevel(self.root)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            # Premium emerald-themed tooltip
            tw.configure(fg_color=("#F2F0E6", "#151D18"))
            tw.attributes("-topmost", True)
            
            label = ctk.CTkLabel(tw, text=text, justify="left",
                                padx=12, pady=8, font=ctk.CTkFont(family="Inter", size=12))
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
            except:
                pass
            self.show_id = None

    def hide(self):
        self._cancel_pending()
        
        if self.tip_window:
            try:
                # Forcefully hide before destroying to prevent visual flickering
                self.tip_window.withdraw()
                self.tip_window.destroy()
            except:
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
        self.title("OSRG")
        self.geometry(f"{config.WINDOW_DEFAULT_WIDTH}x{config.WINDOW_DEFAULT_HEIGHT}")
        self.minsize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)

        # Main Layout: Sidebar (0) and Content (1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Initialize ToolTip Manager
        ToolTipManager.get_instance(self)
        
        # Hide tooltip when app loses focus or is minimized
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
        self.current_repo = None

        self._create_sidebar()
        self._create_main_content()
        self._load_repos()

    def _on_app_focus_out(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager:
            manager.hide()

    def _on_app_minimize(self, event=None):
        manager = ToolTipManager.get_instance()
        if manager:
            manager.hide()

    def _on_app_configure(self, event=None):
        # Hide tooltip when app is resized or moved
        manager = ToolTipManager.get_instance()
        if manager:
            manager.hide()

    def _on_key_press(self, event=None):
        # Hide tooltip when any key is pressed
        manager = ToolTipManager.get_instance()
        if manager:
            manager.hide()

    # Removed _create_header in favor of a unified sidebar design

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="OSRG",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
            text_color=("#2C342C", "#10B981") # Emerald logo for dark mode
        )
        self.logo_label.pack(pady=(40, 30), padx=24, anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("repos", "Repositories"),
            ("trending", "Trending"),
            ("search", "Search"),
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
            
            # Professional touch: Navigation ToolTips
            tip_map = {
                "repos": "View and manage locally cloned repositories",
                "trending": "Discover what's hot in the Open Source world today",
                "search": "Find millions of projects on GitHub",
                "add": "Import any repository by URL",
                "ai": "Analyze code with Project Oracle AI",
                "settings": "Configure OSRG and AI models"
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
        
        self._create_repos_view()
        self._create_trending_view()
        self._create_search_view()
        self._create_add_view()
        self._create_ai_view()
        self._create_settings_view()
        
        self._switch_view("repos")

    def _create_repos_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["repos"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            header,
            text="Repositories",
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
        
        self.repo_list = ctk.CTkFrame(view, fg_color="transparent")
        self.repo_list.pack(fill="both", expand=True, padx=20, pady=10)

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
        
        # Language filter
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
        
        # Trending list
        self.trending_list = ctk.CTkFrame(view, fg_color="transparent")
        self.trending_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            self.trending_list,
            text="Click 'Refresh' to load trending repos",
            text_color="gray"
        ).pack(pady=20)

    def _create_search_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["search"] = view
        
        ctk.CTkLabel(
            view,
            text="Search GitHub Repositories",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Search input
        search_frame = ctk.CTkFrame(view, fg_color="transparent", border_width=0)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Find repositories...",
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
        
        # Language filter for search
        lang_frame = ctk.CTkFrame(view, fg_color="transparent")
        lang_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(lang_frame, text="Language:").pack(side="left", padx=5)
        
        self.search_lang = ctk.CTkComboBox(
            lang_frame,
            values=["", "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#"]
        )
        self.search_lang.pack(side="left", padx=5)
        
        # Results
        self.search_results_list = ctk.CTkFrame(view, fg_color="transparent")
        self.search_results_list.pack(fill="both", expand=True, padx=20, pady=10)

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
            text="Import any GitHub repository by URL or owner/name",
            text_color=("gray50", "gray60")
        ).pack(pady=5)
        
        self.repo_url_entry = ctk.CTkEntry(
            view,
            placeholder_text="e.g. facebook/react",
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
            command=self._add_repo
        ).pack(pady=10)
        
        self.add_status = ctk.CTkLabel(view, text="", font=ctk.CTkFont(size=13))
        self.add_status.pack(pady=20)

    def _create_ai_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["ai"] = view
        
        ctk.CTkLabel(
            view,
            text="Analysis Agent",
            font=ctk.CTkFont(family="Inter", size=28, weight="bold")
        ).pack(anchor="w", padx=20, pady=(30, 10))
        
        model_frame = ctk.CTkFrame(view, fg_color="transparent", border_width=0)
        model_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(model_frame, text="Intelligence Engine", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        self.model_selector = ctk.CTkComboBox(
            model_frame,
            values=config.OLLAMA_MODELS,
            height=36,
            corner_radius=8,
            command=self._change_model
        )
        self.model_selector.set(config.OLLAMA_DEFAULT_MODEL)
        self.model_selector.pack(side="left", fill="x", expand=True)
        
        self.ollama_status = ctk.CTkLabel(model_frame, text="Checking status...", font=ctk.CTkFont(size=12))
        self.ollama_status.pack(side="right", padx=10)
        
        threading.Thread(target=self._check_ollama, daemon=True).start()
        
        input_frame = ctk.CTkFrame(view, corner_radius=12)
        input_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            input_frame,
            text="Enter code snippet to analyze",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
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
        # Professional cleanup: Hide any active tooltip
        manager = ToolTipManager.get_instance()
        if manager: manager.hide()
        
        self._show_view(view_name)
        
        # Highlight active button with high-contrast emerald
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

    def _load_repos(self):
        def load():
            try:
                self.repos = self.repo_manager.list_repos()
                self.after(0, self._display_repos)
            except Exception as e:
                logger.error(f"Error loading repos: {e}")
        
        threading.Thread(target=load, daemon=True).start()

    def _display_repos(self):
        for widget in self.repo_list.winfo_children():
            widget.destroy()
        
        if not self.repos:
            ctk.CTkLabel(
                self.repo_list,
                text="No repositories yet. Click 'Add Repository' to get started!",
                text_color="gray"
            ).pack(pady=20)
            return
        
        for repo in self.repos:
            self._create_repo_card(repo)

    def _create_repo_card(self, repo):
        # Card with 12px radius and 0 border width (removes the "weird lines")
        card = ctk.CTkFrame(self.repo_list, height=140, corner_radius=12, border_width=0)
        card.pack(fill="x", pady=10, padx=10)
        card.grid_propagate(False)
        
        # Repository Identity Section
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=25, pady=20)
        
        repo_name_lbl = ctk.CTkLabel(
            info_frame,
            text=repo["name"],
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            anchor="w"
        )
        repo_name_lbl.pack(fill="x")
        
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
            sync_lbl.pack(fill="x", pady=(4, 0))

        # Semantic Smart Tags
        if repo.get("smart_tags"):
            tags_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            tags_frame.pack(fill="x", pady=(12, 0))
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

        # Professional Action Controls
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", fill="y", padx=25)
        
        inner_btns = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner_btns.pack(expand=True)

        audit_btn = ctk.CTkButton(
            inner_btns,
            text="🏛️ Audit",
            width=80,
            height=32,
            corner_radius=8,
            fg_color=("#5E6C54", "#10B981"),
            hover_color=("#4F5B46", "#059669"),
            text_color="white",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=lambda r=repo: self._run_architecture_audit(r)
        )
        audit_btn.pack(side="left", padx=5)
        ToolTip(audit_btn, "Run Project Oracle Architectural Audit")

        open_btn = ctk.CTkButton(
            inner_btns,
            text="📂 Open",
            width=80,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("#5E6C54", "#10B981"),
            text_color=("#5E6C54", "#10B981"),
            font=ctk.CTkFont(family="Inter", size=12),
            command=lambda p=repo["path"]: self._open_repo(p)
        )
        open_btn.pack(side="left", padx=5)
        ToolTip(open_btn, "Open source code folder in editor")
        
        sync_btn = ctk.CTkButton(
            inner_btns,
            text="🔄 Sync",
            width=80,
            height=32,
            corner_radius=8,
            fg_color=("gray90", "#202924"),
            text_color=("#1D1D1F", "#ECF0ED"),
            hover_color=("gray80", "#2D362F"),
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda p=repo["path"]: self._update_repo(p)
        )
        sync_btn.pack(side="left", padx=5)
        ToolTip(sync_btn, "Update from GitHub and scan for changes")
        
        del_btn = ctk.CTkButton(
            inner_btns,
            text="✕",
            width=32,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            text_color="#FF3B30",
            hover_color=("#FFE5E5", "#3D2525"),
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            command=lambda p=repo["path"]: self._delete_repo(p)
        )
        del_btn.pack(side="left", padx=5)
        ToolTip(del_btn, "Remove project from local storage")

    def _load_trending(self):
        # Clear list
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
            
            ctk.CTkLabel(
                info_frame,
                text=stats_text,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=config.COLORS["dark"]["accent"],
                anchor="w"
            ).pack(fill="x")
            
            # Actions
            btn_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            btn_frame.pack(side="right", fill="y", padx=20)
            
            ctk.CTkButton(
                btn_frame,
                text="Clone",
                width=80,
                height=32,
                corner_radius=8,
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(expand=True)

    def _trending_error(self, error):
        for widget in self.trending_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.trending_list,
            text=f"Error: {error}",
            text_color="#ff4757"
        ).pack(pady=20)

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
            
            # Actions
            btn_frame = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
            btn_frame.pack(side="right", fill="y", padx=20)
            
            ctk.CTkButton(
                btn_frame,
                text="Clone",
                width=80,
                height=32,
                corner_radius=8,
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(expand=True)

    def _search_error(self, error):
        for widget in self.search_results_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.search_results_list,
            text=f"Error: {error}",
            text_color="#ff4757"
        ).pack(pady=20)

    def _clone_from_search(self, repo):
        url = repo.get("clone_url") or f"https://github.com/{repo['full_name']}.git"
        result = self.repo_manager.add_repo(url)
        
        if result.get("status") == "cloned":
            messagebox.showinfo("Success", f"Cloned {result['name']}!")
            self._load_repos()
        elif result.get("status") == "already_exists":
            messagebox.showinfo("Info", "Repository already exists!")
        else:
            messagebox.showerror("Error", result.get("error", "Failed to clone"))

    def _add_repo(self):
        url = self.repo_url_entry.get().strip()
        if not url:
            self.add_status.configure(text="Please enter a repository URL or owner/repo")
            return
        
        self.add_status.configure(text="Cloning repository...")
        
        def clone():
            result = self.repo_manager.add_repo(url)
            self.after(0, lambda: self._add_repo_result(result))
        
        threading.Thread(target=clone, daemon=True).start()

    def _add_repo_result(self, result):
        if result.get("status") == "cloned":
            self.add_status.configure(text=f"Success! Cloned {result['name']}")
            self.repo_url_entry.delete(0, "end")
            self._load_repos()
        elif result.get("status") == "already_exists":
            self.add_status.configure(text=result.get("message", "Already exists"))
        else:
            self.add_status.configure(text=f"Error: {result.get('error', 'Unknown error')}")

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
        # 1. Loading UI - Professional border-free modal
        audit_win = ctk.CTkToplevel(self)
        audit_win.title(f"Oracle Audit: {repo['name']}")
        audit_win.geometry("900x750")
        audit_win.grid_columnconfigure(0, weight=1)
        audit_win.grid_rowconfigure(2, weight=1)
        
        # Header with repo info
        header = ctk.CTkFrame(audit_win, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 10))
        
        title_lbl = ctk.CTkLabel(header, text=f"🏛️ Architectural Audit: {repo['name']}", 
                                font=ctk.CTkFont(family="Inter", size=24, weight="bold"))
        title_lbl.pack(side="left")
        
        # Progress Indicator Frame (Sleek and borderless)
        progress_frame = ctk.CTkFrame(audit_win, height=44, fg_color=("#E8EDE6", "#1D2620"))
        progress_frame.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        status_label = ctk.CTkLabel(progress_frame, text="⚙️ Initializing Project Oracle...",
                                   font=ctk.CTkFont(family="Inter", size=13))
        status_label.pack(pady=8, padx=20, side="left")
        
        # Output Area: Clean typography, zero border
        output_txt = ctk.CTkTextbox(audit_win, font=ctk.CTkFont(family="Consolas", size=13),
                                   fg_color=("#FFFFFF", "#1E2621"), 
                                   text_color=("#1D1D1F", "#ECF0ED"),
                                   border_width=0)
        output_txt.grid(row=2, column=0, sticky="nsew", padx=40, pady=10)
        
        # Footer Action
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
                # 1. Gather Context
                self.after(0, lambda: status_label.configure(text="🔍 Deep Scanning Repository Structure..."))
                context = self.repo_manager.get_project_context(repo["path"])
                if not context or not context.get("file_tree"):
                    raise Exception("No project files found. Is the repository empty?")
                
                # 2. Perform Audit
                self.after(0, lambda: status_label.configure(text="🧠 Reasoning through Project Architecture..."))
                audit = self.ollama.perform_architectural_audit(context)
                if not audit:
                    raise Exception("AI failed to generate an audit report.")
                
                # 3. Suggest Tags
                self.after(0, lambda: status_label.configure(text="🏷️ Generating Semantic Smart Tags..."))
                readme = self.repo_manager.get_repo_readme(repo["path"])
                tags = self.ollama.suggest_smart_tags(readme, context)
                
                # 4. Persistence
                self.after(0, lambda: status_label.configure(text="💾 Persisting insights to Knowledge Base..."))
                from database import get_database
                db = get_database()
                
                # Try multiple lookup strategies for full_name
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
                
                # 5. UI Completion
                self.after(0, lambda a=audit: self._show_audit_results(output_txt, status_label, a))
                self.after(0, self._load_repos) # Refresh list to show tags
                
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
        try:
            import subprocess
            subprocess.Popen(["code", path])
        except:
            self._open_in_explorer(path)

    def _open_in_explorer(self, path):
        try:
            import subprocess
            subprocess.Popen(["explorer", path])
        except Exception as e:
            logger.error(f"Error: {e}")

    def _open_repos_folder(self):
        try:
            import subprocess
            subprocess.Popen(["explorer", str(self.repo_manager.get_repos_path())])
        except Exception as e:
            logger.error(f"Error: {e}")

    def _check_ollama(self):
        available = self.ollama.is_available()
        self.after(0, lambda: self.ollama_status.configure(
            text="Connected" if available else "Not Available",
            text_color="#00d9a0" if available else "#ff4757"
        ))

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
                # Use the new agentic method
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
