export interface RateLimitInfo {
  limit: number;
  remaining: number;
  used: number;
  reset: string | null;
  reset_display: string;
  authenticated: boolean;
  rate_limited: boolean;
}

export interface RemoteRepo {
  name: string;
  full_name: string;
  description: string;
  html_url: string;
  clone_url?: string;
  stars: number;
  forks?: number;
  watchers?: number;
  open_issues?: number;
  license_spdx_id: string;
  language: string;
  topics?: string[];
  good_first_issues?: number;
  difficulty?: string;
  category?: string;
  why?: string;
}

export interface LocalRepo {
  name: string;
  full_name: string;
  path: string;
  license: string;
  last_commit?: string;
  last_commit_date?: string;
  smart_tags?: string[];
}

export interface GoodFirstIssue {
  title: string;
  repo: string;
  repo_url: string;
  html_url: string;
  number: number;
  comments: number;
  labels: string[];
  updated_at?: string;
  state?: string;
}

export interface LicenseInfo {
  name: string;
  spdx: string;
  category: string;
  summary: string;
  can: string[];
  must: string[];
  cannot: string[];
  recommended_for: string;
}

export interface PrStep {
  id?: string;
  title: string;
  detail: string;
  command?: string;
}

export interface PrPhase {
  phase: string;
  subtitle: string;
  steps: PrStep[];
}

export interface GitCommand {
  category: string;
  command: string;
  description: string;
}

export interface OverviewData {
  ok: boolean;
  error?: string;
  repos_path: string;
  local_count: number;
  folders: Record<string, { path: string; count: number }>;
  rate_limit: RateLimitInfo;
  ollama: {
    available: boolean;
    model: string;
    base_url: string;
  };
  starter_repos: RemoteRepo[];
}

export interface OSRGBridge {
  ping: () => Promise<{ ok: boolean; version: string }>;
  get_overview_data: () => Promise<OverviewData>;
  get_rate_limit: (force_refresh?: boolean) => Promise<{ ok: boolean; rate_limit: RateLimitInfo; error?: string }>;
  set_github_token: (token: string) => Promise<{ ok: boolean; rate_limit?: RateLimitInfo; error?: string }>;
  search_trending_repos: (language?: string, force_refresh?: boolean) => Promise<{ ok: boolean; items: RemoteRepo[]; rate_limit?: RateLimitInfo; cached?: boolean; error?: string }>;
  search_repos: (query: string, language?: string, force_refresh?: boolean) => Promise<{ ok: boolean; items: RemoteRepo[]; rate_limit?: RateLimitInfo; error?: string }>;
  get_remote_readme: (full_name: string) => Promise<{ ok: boolean; content: string; found: boolean; error?: string }>;
  search_good_first_issues: (language?: string, topic?: string, force_refresh?: boolean) => Promise<{ ok: boolean; items: GoodFirstIssue[]; error?: string }>;
  get_license_knowledge_base: () => Promise<{ ok: boolean; licenses: Record<string, LicenseInfo> }>;
  get_contributor_guide: () => Promise<{
    ok: boolean;
    workflow: PrPhase[];
    git_essentials: GitCommand[];
    conventional_commits: { type: string; description: string }[];
  }>;
  list_local_repos: (license_filter?: string) => Promise<{ ok: boolean; repos: LocalRepo[]; counts?: Record<string, number>; repos_path?: string; error?: string }>;
  clone_repo: (repo_url: string, license_spdx?: string | null) => Promise<{ ok: boolean; result?: LocalRepo & { status: string }; error?: string }>;
  update_local_repo: (repo_path: string) => Promise<{ ok: boolean; status?: string; error?: string }>;
  update_all_repos: () => Promise<{ ok: boolean; total?: number; updated?: number; error?: string }>;
  delete_local_repo: (repo_path: string) => Promise<{ ok: boolean; status?: string; error?: string }>;
  get_local_readme: (repo_path: string) => Promise<{ ok: boolean; content: string; found: boolean; error?: string }>;
  get_local_file_tree: (repo_path: string, max_files?: number) => Promise<{ ok: boolean; stats: { files?: number; dirs?: number; size_mb?: number }; files: string[]; error?: string }>;
  read_local_file: (repo_path: string, rel_path: string) => Promise<{ ok: boolean; path?: string; size?: number; truncated?: boolean; content?: string; error?: string }>;
  run_architectural_audit: (repo_path: string, full_name?: string, force?: boolean) => Promise<{ ok: boolean; report?: string; smart_tags?: string[]; cached?: boolean; ollama_available?: boolean; error?: string }>;
  open_in_editor: (repo_path: string, preferred?: string) => Promise<{ ok: boolean; error?: string }>;
  open_in_explorer: (repo_path?: string) => Promise<{ ok: boolean; error?: string }>;
  open_external_url: (url: string) => Promise<{ ok: boolean; error?: string }>;
  get_ai_status: () => Promise<{ ok: boolean; available: boolean; models: string[]; current_model?: string; base_url?: string; error?: string }>;
  refresh_ai_models: (base_url?: string) => Promise<{ ok: boolean; available: boolean; models: string[]; current_model?: string; base_url?: string; error?: string }>;
  set_ai_model: (model: string) => Promise<{ ok: boolean; current_model?: string; error?: string }>;
  analyze_code: (code: string, language?: string | null) => Promise<{ ok: boolean; analysis?: string; ollama_available?: boolean; error?: string }>;
  set_ollama_url: (url: string) => Promise<{ ok: boolean; available: boolean; models: string[]; base_url?: string; error?: string }>;
  get_settings: () => Promise<{ ok: boolean; repos_path?: string; has_token?: boolean; ollama_url?: string; ollama_model?: string; rate_limit?: RateLimitInfo; error?: string }>;
}

declare global {
  interface Window {
    pywebview?: {
      api?: OSRGBridge;
    };
  }
}

let bridgeReadyPromise: Promise<OSRGBridge> | null = null;

export function getBridge(): Promise<OSRGBridge> {
  if (window.pywebview?.api) {
    return Promise.resolve(window.pywebview.api);
  }
  if (!bridgeReadyPromise) {
    bridgeReadyPromise = new Promise<OSRGBridge>((resolve, reject) => {
      const deadline = window.setTimeout(() => {
        if (window.pywebview?.api) {
          resolve(window.pywebview.api);
        } else {
          reject(new Error('Desktop bridge (pywebview) is unavailable. Launch via run.py.'));
        }
      }, 6000);

      const handleReady = () => {
        if (window.pywebview?.api) {
          window.clearTimeout(deadline);
          window.removeEventListener('pywebviewready', handleReady);
          resolve(window.pywebview.api);
        }
      };

      window.addEventListener('pywebviewready', handleReady);
    });
  }
  return bridgeReadyPromise;
}
