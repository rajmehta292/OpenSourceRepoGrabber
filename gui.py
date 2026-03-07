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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RepoGrabberApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenSource Repo Grabber")
        self.geometry("1200x800")
        self.minsize(900, 600)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Initialize managers
        self.repo_manager = get_repo_manager()
        self.ollama = get_ollama_client()
        self.github = get_github_client()
        
        self.repos = []
        self.trending_repos = []
        self.search_results = []
        self.current_repo = None

        self._create_header()
        self._create_sidebar()
        self._create_main_content()
        self._load_repos()

    def _create_header(self):
        self.header = ctk.CTkFrame(self, height=50, fg_color="#16213e")
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header.grid_propagate(False)

        ctk.CTkLabel(
            self.header,
            text="OpenSource Repo Grabber",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left", padx=20)

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color="#16213e")
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        nav_items = [
            ("repos", "My Repositories"),
            ("trending", "Trending"),
            ("search", "Search GitHub"),
            ("add", "Add Repository"),
            ("ai", "AI Explain"),
            ("settings", "Settings")
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=40,
                fg_color="#0f3460",
                hover_color="#e94560",
                command=lambda k=key: self._switch_view(k)
            )
            btn.pack(fill="x", padx=10, pady=5)

        # Highlight repos button
        for btn in self.sidebar.winfo_children():
            if hasattr(btn, "cget") and btn.cget("text") == "My Repositories":
                btn.configure(fg_color="#e94560")

        ctk.CTkLabel(
            self.sidebar,
            text="Repository Folder:",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(20, 5), padx=10)

        ctk.CTkLabel(
            self.sidebar,
            text=str(self.repo_manager.get_repos_path()),
            font=ctk.CTkFont(size=9),
            text_color="gray",
            wraplength=180
        ).pack(padx=10)

        ctk.CTkButton(
            self.sidebar,
            text="Open Folder",
            command=self._open_repos_folder
        ).pack(pady=5, padx=10)

    def _create_main_content(self):
        self.content = ctk.CTkFrame(self, fg_color="#1a1a2e")
        self.content.grid(row=1, column=1, sticky="nsew")
        
        self.views = {}
        
        self._create_repos_view()
        self._create_trending_view()
        self._create_search_view()
        self._create_add_view()
        self._create_ai_view()
        self._create_settings_view()
        
        self._show_view("repos")

    def _create_repos_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["repos"] = view
        
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            header,
            text="My Repositories",
            font=ctk.CTkFont(size=18, weight="bold")
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
            width=130,
            command=lambda: webbrowser.open("https://github.com/trending/")
        ).pack(side="right")
        
        ctk.CTkButton(
            header,
            text="Refresh",
            width=80,
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
        search_frame = ctk.CTkFrame(view, fg_color="#0f3460")
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search for repositories (e.g., machine learning)",
            height=40
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.search_entry.bind("<Return>", lambda e: self._search_repos())
        
        ctk.CTkButton(
            search_frame,
            text="Search",
            width=100,
            command=self._search_repos
        ).pack(side="right", padx=10, pady=10)
        
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
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            view,
            text="Enter GitHub repository URL or owner/repo:",
            text_color="gray"
        ).pack(pady=5)
        
        self.repo_url_entry = ctk.CTkEntry(
            view,
            placeholder_text="e.g., facebook/react or https://github.com/facebook/react",
            width=400,
            height=40
        )
        self.repo_url_entry.pack(pady=10)
        
        ctk.CTkButton(
            view,
            text="Clone Repository",
            width=200,
            height=40,
            fg_color="#00d9a0",
            command=self._add_repo
        ).pack(pady=10)
        
        self.add_status = ctk.CTkLabel(view, text="")
        self.add_status.pack(pady=10)

    def _create_ai_view(self):
        view = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.views["ai"] = view
        
        ctk.CTkLabel(
            view,
            text="AI Code Explainer (Ollama)",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        model_frame = ctk.CTkFrame(view, fg_color="#0f3460")
        model_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(model_frame, text="Model:").pack(side="left", padx=10)
        
        self.model_selector = ctk.CTkComboBox(
            model_frame,
            values=config.OLLAMA_MODELS,
            command=self._change_model
        )
        self.model_selector.set(config.OLLAMA_DEFAULT_MODEL)
        self.model_selector.pack(side="left", padx=10, fill="x", expand=True)
        
        self.ollama_status = ctk.CTkLabel(model_frame, text="Checking...", text_color="gray")
        self.ollama_status.pack(side="right", padx=10)
        
        threading.Thread(target=self._check_ollama, daemon=True).start()
        
        input_frame = ctk.CTkFrame(view, fg_color="#0f3460")
        input_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            input_frame,
            text="Paste code or ask about a repository:",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.code_input = ctk.CTkTextbox(input_frame, height=150)
        self.code_input.pack(fill="x", padx=10, pady=5)
        
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Explain Code",
            fg_color="#00d9a0",
            command=self._explain_code
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Clear",
            command=self._clear_ai
        ).pack(side="right", padx=5)
        
        response_frame = ctk.CTkFrame(view, fg_color="#0f3460")
        response_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(response_frame, text="Response:").pack(anchor="w", padx=10, pady=(10, 5))
        
        self.ai_response = ctk.CTkTextbox(response_frame, height=250)
        self.ai_response.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkButton(
            response_frame,
            text="Copy Response",
            command=self._copy_response
        ).pack(pady=10)

    def _create_settings_view(self):
        view = ctk.CTkFrame(self.content, fg_color="transparent")
        self.views["settings"] = view
        
        ctk.CTkLabel(
            view,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            view,
            text="Repositories Folder:",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(
            view,
            text=str(self.repo_manager.get_repos_path()),
            text_color="gray"
        ).pack(anchor="w", padx=20)
        
        ctk.CTkButton(
            view,
            text="Open in Explorer",
            command=self._open_repos_folder
        ).pack(anchor="w", padx=20, pady=10)
        
        ctk.CTkLabel(
            view,
            text="Ollama Settings:",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(view, text="URL:").pack(anchor="w", padx=20)
        
        self.ollama_url_entry = ctk.CTkEntry(view, width=300)
        self.ollama_url_entry.insert(0, self.ollama.base_url)
        self.ollama_url_entry.pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkButton(
            view,
            text="Save Ollama URL",
            command=self._save_ollama_url
        ).pack(anchor="w", padx=20, pady=10)

    def _show_view(self, view_name):
        for view in self.views.values():
            view.grid_forget()
        
        view = self.views[view_name]
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _switch_view(self, view_name):
        self._show_view(view_name)
        
        colors = {"repos": "#e94560", "trending": "#e94560", "search": "#e94560", 
                  "add": "#e94560", "ai": "#e94560", "settings": "#e94560"}
        
        for btn in self.sidebar.winfo_children():
            if hasattr(btn, "cget"):
                try:
                    text = btn.cget("text")
                    if text in colors:
                        btn.configure(fg_color=colors.get(text, "#0f3460"))
                except:
                    pass

    def _load_repos(self):
        self.repos = self.repo_manager.list_repos()
        
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
        card = ctk.CTkFrame(self.repo_list, fg_color="#0f3460")
        card.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            card,
            text=repo["name"],
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            card,
            text=repo["path"],
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(anchor="w", padx=15)
        
        if repo.get("last_update"):
            ctk.CTkLabel(
                card,
                text=f"Updated: {repo['last_update'][:10]}",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            ).pack(anchor="w", padx=15)
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=15, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Open",
            width=70,
            height=28,
            command=lambda p=repo["path"]: self._open_repo(p)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="Update",
            width=70,
            height=28,
            command=lambda p=repo["path"]: self._update_repo(p)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="Explorer",
            width=80,
            height=28,
            command=lambda p=repo["path"]: self._open_in_explorer(p)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="Delete",
            width=70,
            height=28,
            fg_color="#ff4757",
            command=lambda p=repo["path"]: self._delete_repo(p)
        ).pack(side="left", padx=2)

    def _load_trending(self):
        # Clear list
        for widget in self.trending_list.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.trending_list,
            text="Loading trending repos...",
            text_color="gray"
        ).pack(pady=20)
        
        def load():
            try:
                lang = self.trending_lang.get()
                language = "" if lang == "All" else lang
                
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
            ).pack(pady=20)
            return
        
        for repo in repos:
            card = ctk.CTkFrame(self.trending_list, fg_color="#0f3460")
            card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                card,
                text=f"{repo['full_name']}",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w", padx=15, pady=(10, 5))
            
            desc = repo.get("description", "No description")
            if desc:
                ctk.CTkLabel(
                    card,
                    text=desc[:100] + "..." if len(desc) > 100 else desc,
                    font=ctk.CTkFont(size=11),
                    text_color="gray"
                ).pack(anchor="w", padx=15)
            
            stats = f"⭐ {repo.get('stargazers_count', 0)}  🍴 {repo.get('forks_count', 0)}"
            if repo.get("language"):
                stats += f"  💻 {repo['language']}"
            
            ctk.CTkLabel(
                card,
                text=stats,
                font=ctk.CTkFont(size=11)
            ).pack(anchor="w", padx=15, pady=5)
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(anchor="w", padx=15, pady=10)
            
            ctk.CTkButton(
                btn_frame,
                text="Clone",
                width=70,
                height=28,
                fg_color="#00d9a0",
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(side="left", padx=2)
            
            ctk.CTkButton(
                btn_frame,
                text="View",
                width=70,
                height=28,
                command=lambda u=repo.get("html_url"): webbrowser.open(u)
            ).pack(side="left", padx=2)

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
        
        def search():
            try:
                lang = self.search_lang.get()
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
            ).pack(pady=20)
            return
        
        for repo in repos:
            card = ctk.CTkFrame(self.search_results_list, fg_color="#0f3460")
            card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                card,
                text=f"{repo['full_name']}",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w", padx=15, pady=(10, 5))
            
            desc = repo.get("description", "No description")
            if desc:
                ctk.CTkLabel(
                    card,
                    text=desc[:100] + "..." if len(desc) > 100 else desc,
                    font=ctk.CTkFont(size=11),
                    text_color="gray"
                ).pack(anchor="w", padx=15)
            
            stats = f"⭐ {repo.get('stargazers_count', 0)}  🍴 {repo.get('forks_count', 0)}"
            if repo.get("language"):
                stats += f"  💻 {repo['language']}"
            
            ctk.CTkLabel(
                card,
                text=stats,
                font=ctk.CTkFont(size=11)
            ).pack(anchor="w", padx=15, pady=5)
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(anchor="w", padx=15, pady=10)
            
            ctk.CTkButton(
                btn_frame,
                text="Clone",
                width=70,
                height=28,
                fg_color="#00d9a0",
                command=lambda r=repo: self._clone_from_search(r)
            ).pack(side="left", padx=2)
            
            ctk.CTkButton(
                btn_frame,
                text="View",
                width=70,
                height=28,
                command=lambda u=repo.get("html_url"): webbrowser.open(u)
            ).pack(side="left", padx=2)

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
        result = self.repo_manager.update_repo(path)
        if result.get("status") == "updated":
            messagebox.showinfo("Success", "Repository updated!")
        else:
            messagebox.showerror("Error", result.get("error", "Update failed"))
        self._load_repos()

    def _update_all_repos(self):
        results = self.repo_manager.update_all_repos()
        success = sum(1 for r in results if r.get("status") == "updated")
        messagebox.showinfo("Update Complete", f"Updated {success} of {len(results)} repositories")
        self._load_repos()

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
        self.ai_response.insert("1.0", "Analyzing...")
        
        def run():
            response = self.ollama.explain_code(code)
            self.after(0, lambda: self._show_ai_response(response))
        
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
        self._check_ollama()
        messagebox.showinfo("Saved", "Ollama URL updated!")


def main():
    app = RepoGrabberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
