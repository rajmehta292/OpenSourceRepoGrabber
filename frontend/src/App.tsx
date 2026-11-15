import { useCallback, useEffect, useState } from 'react';
import { AppShell } from '@astryxdesign/core/AppShell';
import { Badge } from '@astryxdesign/core/Badge';
import { SideNav, SideNavHeading, SideNavItem, SideNavSection } from '@astryxdesign/core/SideNav';
import { Switch } from '@astryxdesign/core/Switch';
import { Text } from '@astryxdesign/core/Text';
import { Theme } from '@astryxdesign/core/theme';
import { ToastViewport, useToast } from '@astryxdesign/core/Toast';
import { VStack } from '@astryxdesign/core/VStack';
import {
  Compass,
  Flame,
  FolderGit2,
  GraduationCap,
  PlusCircle,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react';
import {
  getBridge,
  type GitCommand,
  type GoodFirstIssue,
  type LicenseInfo,
  type LocalRepo,
  type OverviewData,
  type PrPhase,
  type RateLimitInfo,
  type RemoteRepo,
} from './api/bridge';
import { defaultThemeSlug, themes } from './astryx-themes';
import {
  AuditDialog,
  ConfirmDeleteDialog,
  FileExplorerDialog,
  ReadmeDialog,
} from './components/Modals';
import { SearchView, TrendingView } from './views/DiscoveryViews';
import { LaunchpadView } from './views/LaunchpadView';
import { OverviewView, type NavTab } from './views/OverviewView';
import { RepositoriesView } from './views/RepositoriesView';
import { AddRepoView, AiExplainView, SettingsView } from './views/StudioViews';

const THEME_STORAGE_KEY = 'osrg.theme_mode.v1';

function OSRGStudio() {
  const toast = useToast();

  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      return saved ? saved === 'dark' : true;
    } catch {
      return true;
    }
  });

  // Overview & system status
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);

  // Local repos
  const [localRepos, setLocalRepos] = useState<LocalRepo[]>([]);
  const [localCounts, setLocalCounts] = useState<Record<string, number>>({});
  const [reposPath, setReposPath] = useState('');
  const [loadingLocal, setLoadingLocal] = useState(false);
  const [updatingAll, setUpdatingAll] = useState(false);
  const [syncingMap, setSyncingMap] = useState<Record<string, boolean>>({});

  // Discovery: Trending (keyed client cache by language)
  const [trendingLang, setTrendingLang] = useState('');
  const [trendingCache, setTrendingCache] = useState<Record<string, RemoteRepo[]>>({});
  const [loadingTrending, setLoadingTrending] = useState(false);

  // Discovery: Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLang, setSearchLang] = useState('All');
  const [searchResults, setSearchResults] = useState<RemoteRepo[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [loadingSearch, setLoadingSearch] = useState(false);

  // OSS Launchpad
  const [issueLang, setIssueLang] = useState('All');
  const [issueCache, setIssueCache] = useState<Record<string, GoodFirstIssue[]>>({});
  const [loadingIssues, setLoadingIssues] = useState(false);
  const [licenses, setLicenses] = useState<Record<string, LicenseInfo>>({});
  const [workflow, setWorkflow] = useState<PrPhase[]>([]);
  const [gitEssentials, setGitEssentials] = useState<GitCommand[]>([]);
  const [conventionalCommits, setConventionalCommits] = useState<{ type: string; description: string }[]>([]);

  // AI Explain
  const [aiAvailable, setAiAvailable] = useState(false);
  const [aiModels, setAiModels] = useState<string[]>([]);
  const [aiModel, setAiModel] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');

  // Cloning & action tracking
  const [cloningMap, setCloningMap] = useState<Record<string, boolean>>({});

  // Shared Modals
  const [readmeState, setReadmeState] = useState<{
    isOpen: boolean;
    title: string;
    content: string;
    loading: boolean;
    githubUrl?: string;
    cloneTarget?: { url: string; spdx?: string; fullName: string };
  }>({ isOpen: false, title: '', content: '', loading: false });

  const [explorerState, setExplorerState] = useState<{
    isOpen: boolean;
    repoName: string;
    repoPath: string;
  }>({ isOpen: false, repoName: '', repoPath: '' });

  const [auditState, setAuditState] = useState<{
    isOpen: boolean;
    repoName: string;
    repoPath: string;
    fullName: string;
  }>({ isOpen: false, repoName: '', repoPath: '', fullName: '' });

  const [deleteTarget, setDeleteTarget] = useState<LocalRepo | null>(null);
  const [deleting, setDeleting] = useState(false);

  const toggleDarkMode = (checked: boolean) => {
    setDarkMode(checked);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, checked ? 'dark' : 'light');
    } catch {
      // Ignore
    }
  };

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const api = await getBridge();
      const res = await api.get_overview_data();
      if (res.ok) {
        setOverview(res);
        setReposPath(res.repos_path);
        setRateLimit(res.rate_limit);
        setAiAvailable(res.ollama.available);
        setAiModel(res.ollama.model);
        setOllamaUrl(res.ollama.base_url);
      }
    } catch (e) {
      toast({ body: `Startup check failed: ${String(e)}`, type: 'error' });
    } finally {
      setLoadingOverview(false);
    }
  }, [toast]);

  const loadLocalRepos = useCallback(async () => {
    setLoadingLocal(true);
    try {
      const api = await getBridge();
      const res = await api.list_local_repos('ALL');
      if (res.ok) {
        setLocalRepos(res.repos || []);
        setLocalCounts(res.counts || {});
        if (res.repos_path) setReposPath(res.repos_path);
      }
    } finally {
      setLoadingLocal(false);
    }
  }, []);

  const loadTrending = useCallback(
    async (lang: string, force = false) => {
      const key = lang.toLowerCase() || 'all';
      if (!force && trendingCache[key]) return;
      setLoadingTrending(true);
      try {
        const api = await getBridge();
        const res = await api.search_trending_repos(lang, force);
        if (res.ok) {
          setTrendingCache((prev) => ({ ...prev, [key]: res.items || [] }));
          if (res.rate_limit) setRateLimit(res.rate_limit);
        } else {
          toast({ body: res.error || 'Failed to load trending repos', type: 'error' });
        }
      } catch (e) {
        toast({ body: String(e), type: 'error' });
      } finally {
        setLoadingTrending(false);
      }
    },
    [trendingCache, toast]
  );

  const loadGoodFirstIssues = useCallback(
    async (lang: string, force = false) => {
      const key = lang.toLowerCase() || 'all';
      if (!force && issueCache[key]) return;
      setLoadingIssues(true);
      try {
        const api = await getBridge();
        const res = await api.search_good_first_issues(lang, '', force);
        if (res.ok) {
          setIssueCache((prev) => ({ ...prev, [key]: res.items || [] }));
        } else {
          toast({ body: res.error || 'Failed to fetch issues', type: 'error' });
        }
      } finally {
        setLoadingIssues(false);
      }
    },
    [issueCache, toast]
  );

  const loadAiStatus = useCallback(async () => {
    try {
      const api = await getBridge();
      const res = await api.get_ai_status();
      if (res.ok) {
        setAiAvailable(res.available);
        setAiModels(res.models || []);
        if (res.current_model) setAiModel(res.current_model);
        if (res.base_url) setOllamaUrl(res.base_url);
      }
    } catch {
      // Ignore
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  // Lazy load tab data only when visited
  useEffect(() => {
    if (activeTab === 'repositories' && localRepos.length === 0) {
      void loadLocalRepos();
    } else if (activeTab === 'trending') {
      void loadTrending(trendingLang, false);
    } else if (activeTab === 'launchpad') {
      void loadGoodFirstIssues(issueLang, false);
      if (Object.keys(licenses).length === 0 || workflow.length === 0) {
        void getBridge().then(async (api) => {
          const [licRes, guideRes] = await Promise.all([
            api.get_license_knowledge_base(),
            api.get_contributor_guide(),
          ]);
          if (licRes.ok) setLicenses(licRes.licenses);
          if (guideRes.ok) {
            setWorkflow(guideRes.workflow);
            setGitEssentials(guideRes.git_essentials);
            setConventionalCommits(guideRes.conventional_commits);
          }
        });
      }
    } else if (activeTab === 'ai') {
      void loadAiStatus();
    }
  }, [
    activeTab,
    localRepos.length,
    trendingLang,
    issueLang,
    licenses,
    workflow.length,
    loadLocalRepos,
    loadTrending,
    loadGoodFirstIssues,
    loadAiStatus,
  ]);

  // Keyboard shortcut: Ctrl+F -> Search tab
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'f' || e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        setActiveTab('search');
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleOpenGitHub = async (repo: RemoteRepo) => {
    const api = await getBridge();
    const url = repo.html_url || `https://github.com/${repo.full_name}`;
    await api.open_external_url(url);
  };

  const handleOpenExternal = async (url: string) => {
    const api = await getBridge();
    await api.open_external_url(url);
  };

  const handlePreviewRemoteReadme = async (repo: RemoteRepo) => {
    setReadmeState({
      isOpen: true,
      title: repo.full_name,
      content: '',
      loading: true,
      githubUrl: repo.html_url || `https://github.com/${repo.full_name}`,
      cloneTarget: {
        url: repo.clone_url || `https://github.com/${repo.full_name}.git`,
        spdx: repo.license_spdx_id,
        fullName: repo.full_name,
      },
    });
    try {
      const api = await getBridge();
      const res = await api.get_remote_readme(repo.full_name);
      setReadmeState((prev) => ({
        ...prev,
        loading: false,
        content: res.found ? res.content : '',
      }));
    } catch {
      setReadmeState((prev) => ({ ...prev, loading: false, content: '' }));
    }
  };

  const handlePreviewLocalReadme = async (repo: LocalRepo) => {
    setReadmeState({
      isOpen: true,
      title: repo.full_name || repo.name,
      content: '',
      loading: true,
    });
    try {
      const api = await getBridge();
      const res = await api.get_local_readme(repo.path);
      setReadmeState((prev) => ({
        ...prev,
        loading: false,
        content: res.found ? res.content : '',
      }));
    } catch {
      setReadmeState((prev) => ({ ...prev, loading: false, content: '' }));
    }
  };

  const handleCloneRepo = async (repoUrlOrFullName: string, fullName: string, licenseSpdx?: string) => {
    setCloningMap((prev) => ({ ...prev, [fullName]: true }));
    toast({ body: `Cloning ${fullName}...`, uniqueID: `clone-${fullName}` });
    try {
      const api = await getBridge();
      const res = await api.clone_repo(repoUrlOrFullName, licenseSpdx || null);
      if (res.ok && res.result) {
        toast({
          body: `Cloned ${fullName} into ${res.result.license}`,
          uniqueID: `clone-${fullName}`,
        });
        await Promise.all([loadLocalRepos(), loadOverview()]);
      } else {
        toast({
          body: res.error || `Failed to clone ${fullName}`,
          type: 'error',
          uniqueID: `clone-${fullName}`,
        });
      }
    } catch (e) {
      toast({ body: String(e), type: 'error' });
    } finally {
      setCloningMap((prev) => ({ ...prev, [fullName]: false }));
    }
  };

  const handleSearchRepos = async (query: string, lang: string) => {
    const cleaned = query.trim();
    if (!cleaned) return;
    setSearchQuery(cleaned);
    setSearchLang(lang);
    setHasSearched(true);
    setLoadingSearch(true);
    try {
      const api = await getBridge();
      const res = await api.search_repos(cleaned, lang, false);
      if (res.ok) {
        setSearchResults(res.items || []);
        if (res.rate_limit) setRateLimit(res.rate_limit);
      } else {
        toast({ body: res.error || 'Search failed', type: 'error' });
      }
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleSyncOne = async (repo: LocalRepo) => {
    setSyncingMap((prev) => ({ ...prev, [repo.path]: true }));
    try {
      const api = await getBridge();
      const res = await api.update_local_repo(repo.path);
      if (res.ok) {
        toast({ body: `Synced ${repo.name}: ${res.status || 'up to date'}` });
        await loadLocalRepos();
      } else {
        toast({ body: res.error || 'Sync failed', type: 'error' });
      }
    } finally {
      setSyncingMap((prev) => ({ ...prev, [repo.path]: false }));
    }
  };

  const handleUpdateAll = async () => {
    setUpdatingAll(true);
    try {
      const api = await getBridge();
      const res = await api.update_all_repos();
      if (res.ok) {
        toast({ body: `Updated ${res.updated ?? 0} of ${res.total ?? 0} repositories` });
        await loadLocalRepos();
      } else {
        toast({ body: res.error || 'Update all failed', type: 'error' });
      }
    } finally {
      setUpdatingAll(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const api = await getBridge();
      const res = await api.delete_local_repo(deleteTarget.path);
      if (res.ok) {
        toast({ body: `Deleted ${deleteTarget.name}` });
        setDeleteTarget(null);
        await Promise.all([loadLocalRepos(), loadOverview()]);
      } else {
        toast({ body: res.error || 'Delete failed', type: 'error' });
      }
    } finally {
      setDeleting(false);
    }
  };

  const trendingItems = trendingCache[trendingLang.toLowerCase() || 'all'] || [];
  const gfiItems = issueCache[issueLang.toLowerCase() || 'all'] || [];

  const sideNav = (
    <SideNav
      aria-label="Primary navigation"
      collapsible
      resizable={{ defaultWidth: 248, minWidth: 210, maxWidth: 320 }}
      header={
        <SideNavHeading
          heading="OSRG"
          subheading="OSS Studio"
          headerEndContent={
            rateLimit ? (
              <Badge
                variant={rateLimit.authenticated ? 'green' : 'neutral'}
                label={`${rateLimit.remaining}/${rateLimit.limit}`}
              />
            ) : undefined
          }
        />
      }
      footer={
        <VStack gap={2}>
          <Switch
            label="Night Mode"
            size="sm"
            labelSpacing="spread"
            width="100%"
            value={darkMode}
            onChange={toggleDarkMode}
          />
          <Text size="sm" color="secondary">
            Ctrl+F: Search · Astryx UI
          </Text>
        </VStack>
      }
    >
      <SideNavSection title="Discover">
        <SideNavItem
          label="Overview Hub"
          icon={Compass}
          isSelected={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
        />
        <SideNavItem
          label="Trending"
          icon={Flame}
          isSelected={activeTab === 'trending'}
          onClick={() => setActiveTab('trending')}
        />
        <SideNavItem
          label="Search GitHub"
          icon={Search}
          isSelected={activeTab === 'search'}
          onClick={() => setActiveTab('search')}
        />
        <SideNavItem
          label="OSS Launchpad"
          icon={GraduationCap}
          isSelected={activeTab === 'launchpad'}
          onClick={() => setActiveTab('launchpad')}
        />
      </SideNavSection>

      <SideNavSection title="Workspace">
        <SideNavItem
          label="Repositories"
          icon={FolderGit2}
          isSelected={activeTab === 'repositories'}
          endContent={
            overview?.local_count !== undefined ? (
              <Badge variant="neutral" label={String(overview.local_count)} />
            ) : undefined
          }
          onClick={() => setActiveTab('repositories')}
        />
        <SideNavItem
          label="Add New"
          icon={PlusCircle}
          isSelected={activeTab === 'add'}
          onClick={() => setActiveTab('add')}
        />
        <SideNavItem
          label="AI Explain"
          icon={Sparkles}
          isSelected={activeTab === 'ai'}
          onClick={() => setActiveTab('ai')}
        />
        <SideNavItem
          label="Settings"
          icon={Settings}
          isSelected={activeTab === 'settings'}
          onClick={() => setActiveTab('settings')}
        />
      </SideNavSection>
    </SideNav>
  );

  return (
    <Theme theme={themes[defaultThemeSlug]} mode={darkMode ? 'dark' : 'light'}>
      <AppShell height="fill" sideNav={sideNav}>
        {activeTab === 'overview' && (
          <OverviewView
            data={overview}
            loading={loadingOverview}
            cloningMap={cloningMap}
            onRefresh={() => void loadOverview()}
            onNavigate={setActiveTab}
            onOpenExplorer={() => void getBridge().then((api) => api.open_in_explorer(''))}
            onOpenGitHub={(repo) => void handleOpenGitHub(repo)}
            onPreviewReadme={(repo) => void handlePreviewRemoteReadme(repo)}
            onClone={(repo) =>
              void handleCloneRepo(
                repo.clone_url || `https://github.com/${repo.full_name}.git`,
                repo.full_name,
                repo.license_spdx_id
              )
            }
          />
        )}

        {activeTab === 'repositories' && (
          <RepositoriesView
            repos={localRepos}
            counts={localCounts}
            reposPath={reposPath}
            loading={loadingLocal}
            updatingAll={updatingAll}
            syncingMap={syncingMap}
            onRefresh={() => void loadLocalRepos()}
            onUpdateAll={() => void handleUpdateAll()}
            onOpenFolder={() => void getBridge().then((api) => api.open_in_explorer(''))}
            onNavigateAdd={() => setActiveTab('add')}
            onNavigateTrending={() => setActiveTab('trending')}
            onInspectFiles={(repo) =>
              setExplorerState({ isOpen: true, repoName: repo.name, repoPath: repo.path })
            }
            onReadReadme={(repo) => void handlePreviewLocalReadme(repo)}
            onAudit={(repo) =>
              setAuditState({
                isOpen: true,
                repoName: repo.name,
                repoPath: repo.path,
                fullName: repo.full_name,
              })
            }
            onOpenIde={(repo) =>
              void getBridge().then(async (api) => {
                const r = await api.open_in_editor(repo.path, 'auto');
                if (!r.ok) toast({ body: 'No supported IDE executable found in PATH', type: 'error' });
              })
            }
            onSync={(repo) => void handleSyncOne(repo)}
            onRequestDelete={setDeleteTarget}
          />
        )}

        {activeTab === 'trending' && (
          <TrendingView
            items={trendingItems}
            language={trendingLang}
            loading={loadingTrending}
            cloningMap={cloningMap}
            onSelectLanguage={(lang) => {
              setTrendingLang(lang);
              void loadTrending(lang, false);
            }}
            onRefresh={() => void loadTrending(trendingLang, true)}
            onOpenGitHub={(repo) => void handleOpenGitHub(repo)}
            onPreviewReadme={(repo) => void handlePreviewRemoteReadme(repo)}
            onClone={(repo) =>
              void handleCloneRepo(
                repo.clone_url || `https://github.com/${repo.full_name}.git`,
                repo.full_name,
                repo.license_spdx_id
              )
            }
          />
        )}

        {activeTab === 'search' && (
          <SearchView
            query={searchQuery}
            language={searchLang}
            items={searchResults}
            loading={loadingSearch}
            hasSearched={hasSearched}
            cloningMap={cloningMap}
            onSearch={(q, l) => void handleSearchRepos(q, l)}
            onOpenGitHub={(repo) => void handleOpenGitHub(repo)}
            onPreviewReadme={(repo) => void handlePreviewRemoteReadme(repo)}
            onClone={(repo) =>
              void handleCloneRepo(
                repo.clone_url || `https://github.com/${repo.full_name}.git`,
                repo.full_name,
                repo.license_spdx_id
              )
            }
          />
        )}

        {activeTab === 'launchpad' && (
          <LaunchpadView
            issues={gfiItems}
            issueLanguage={issueLang}
            loadingIssues={loadingIssues}
            licenses={licenses}
            workflow={workflow}
            gitEssentials={gitEssentials}
            conventionalCommits={conventionalCommits}
            cloningMap={cloningMap}
            onSelectIssueLanguage={(lang) => {
              setIssueLang(lang);
              void loadGoodFirstIssues(lang, false);
            }}
            onRefreshIssues={() => void loadGoodFirstIssues(issueLang, true)}
            onOpenExternal={(url) => void handleOpenExternal(url)}
            onCloneByFullName={(fullName) =>
              void handleCloneRepo(`https://github.com/${fullName}.git`, fullName)
            }
          />
        )}

        {activeTab === 'add' && (
          <AddRepoView
            onCloned={(res) => {
              toast({ body: `Cloned ${res.full_name || res.name} successfully` });
              void Promise.all([loadLocalRepos(), loadOverview()]);
            }}
          />
        )}

        {activeTab === 'ai' && (
          <AiExplainView
            available={aiAvailable}
            models={aiModels}
            currentModel={aiModel}
            onRefreshModels={() => void loadAiStatus()}
            onSelectModel={(model) => {
              setAiModel(model);
              void getBridge().then((api) => api.set_ai_model(model));
            }}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            reposPath={reposPath}
            hasToken={Boolean(rateLimit?.authenticated)}
            rateLimit={rateLimit}
            ollamaUrl={ollamaUrl}
            onTokenSaved={(rate) => {
              setRateLimit(rate);
              void loadOverview();
            }}
            onOllamaUrlSaved={() => void loadAiStatus()}
            onOpenStorageFolder={() => void getBridge().then((api) => api.open_in_explorer(''))}
          />
        )}

        <ReadmeDialog
          isOpen={readmeState.isOpen}
          onClose={() => setReadmeState((prev) => ({ ...prev, isOpen: false }))}
          title={readmeState.title}
          content={readmeState.content}
          loading={readmeState.loading}
          githubUrl={readmeState.githubUrl}
          cloning={
            readmeState.cloneTarget ? Boolean(cloningMap[readmeState.cloneTarget.fullName]) : false
          }
          onClone={
            readmeState.cloneTarget
              ? () => {
                  const target = readmeState.cloneTarget!;
                  void handleCloneRepo(target.url, target.fullName, target.spdx);
                }
              : undefined
          }
        />

        <FileExplorerDialog
          isOpen={explorerState.isOpen}
          onClose={() => setExplorerState((prev) => ({ ...prev, isOpen: false }))}
          repoName={explorerState.repoName}
          repoPath={explorerState.repoPath}
        />

        <AuditDialog
          isOpen={auditState.isOpen}
          onClose={() => setAuditState((prev) => ({ ...prev, isOpen: false }))}
          repoName={auditState.repoName}
          repoPath={auditState.repoPath}
          fullName={auditState.fullName}
        />

        <ConfirmDeleteDialog
          isOpen={Boolean(deleteTarget)}
          repoName={deleteTarget?.name || ''}
          deleting={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void handleConfirmDelete()}
        />

        <ToastViewport position="bottomEnd" />
      </AppShell>
    </Theme>
  );
}

export default function App() {
  return <OSRGStudio />;
}
