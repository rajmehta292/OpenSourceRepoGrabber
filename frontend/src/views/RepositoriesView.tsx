import { useMemo, useState } from 'react';
import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { Spinner } from '@astryxdesign/core/Spinner';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { VStack } from '@astryxdesign/core/VStack';
import { FolderGit2, FolderOpen, PlusCircle, RefreshCw } from 'lucide-react';
import type { LocalRepo } from '../api/bridge';
import { LocalRepoCard } from '../components/RepoCard';

export interface RepositoriesViewProps {
  repos: LocalRepo[];
  counts: Record<string, number>;
  reposPath: string;
  loading: boolean;
  updatingAll: boolean;
  syncingMap: Record<string, boolean>;
  onRefresh: () => void;
  onUpdateAll: () => void;
  onOpenFolder: () => void;
  onNavigateAdd: () => void;
  onNavigateTrending: () => void;
  onInspectFiles: (repo: LocalRepo) => void;
  onReadReadme: (repo: LocalRepo) => void;
  onAudit: (repo: LocalRepo) => void;
  onOpenIde: (repo: LocalRepo) => void;
  onSync: (repo: LocalRepo) => void;
  onRequestDelete: (repo: LocalRepo) => void;
}

export function RepositoriesView({
  repos,
  counts,
  reposPath,
  loading,
  updatingAll,
  syncingMap,
  onRefresh,
  onUpdateAll,
  onOpenFolder,
  onNavigateAdd,
  onNavigateTrending,
  onInspectFiles,
  onReadReadme,
  onAudit,
  onOpenIde,
  onSync,
  onRequestDelete,
}: RepositoriesViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [licenseFilter, setLicenseFilter] = useState('ALL');

  const licenseBuckets = useMemo(() => {
    const keys = Object.keys(counts).filter((k) => k !== 'ALL' && counts[k] > 0);
    return ['ALL', ...keys.sort()];
  }, [counts]);

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return repos.filter((r) => {
      if (licenseFilter !== 'ALL' && (r.license || 'Other') !== licenseFilter) {
        return false;
      }
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        r.full_name.toLowerCase().includes(q) ||
        (r.last_commit || '').toLowerCase().includes(q) ||
        (r.smart_tags || []).some((t) => t.toLowerCase().includes(q))
      );
    });
  }, [repos, licenseFilter, searchQuery]);

  return (
    <div className="osrg-page">
      <VStack gap={4}>
        <HStack justify="between" align="center" wrap="wrap" gap={3}>
          <VStack gap={1}>
            <HStack gap={2} align="center">
              <Heading level={1}>Local Repositories</Heading>
              <Badge variant="green" label={`${repos.length} cloned`} />
            </HStack>
            <Text size="sm" color="secondary" type="code">
              {reposPath || 'Workspace loading...'}
            </Text>
          </VStack>

          <HStack gap={2} wrap="wrap">
            <Button
              label={updatingAll ? 'Updating All...' : 'Update All'}
              size="sm"
              variant="secondary"
              isLoading={updatingAll}
              icon={<RefreshCw size={14} />}
              onClick={onUpdateAll}
            />
            <Button
              label="Open Folder"
              size="sm"
              variant="ghost"
              icon={<FolderOpen size={14} />}
              onClick={onOpenFolder}
            />
            <Button
              label="Refresh"
              size="sm"
              variant="ghost"
              isLoading={loading}
              onClick={onRefresh}
            />
            <Button
              label="Add Repo"
              size="sm"
              variant="primary"
              icon={<PlusCircle size={14} />}
              onClick={onNavigateAdd}
            />
          </HStack>
        </HStack>

        <HStack gap={3} align="center" wrap="wrap">
          <div style={{ flex: '1 1 280px', maxWidth: 440 }}>
            <TextInput
              label="Filter local repositories"
              isLabelHidden
              hasClear
              placeholder="Search name, smart tag, or last commit..."
              value={searchQuery}
              onChange={setSearchQuery}
            />
          </div>

          <div className="osrg-chip-row">
            {licenseBuckets.map((lic) => (
              <button
                key={lic}
                type="button"
                className="osrg-filter-pill"
                data-active={licenseFilter === lic}
                onClick={() => setLicenseFilter(lic)}
              >
                {lic} ({counts[lic] ?? 0})
              </button>
            ))}
          </div>
        </HStack>

        {loading && repos.length === 0 ? (
          <HStack gap={2} align="center" style={{ padding: '40px 8px' }}>
            <Spinner size="md" />
            <Text color="secondary">Scanning local license folders...</Text>
          </HStack>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<FolderGit2 size={36} />}
            title={repos.length === 0 ? 'No local repositories yet' : 'No matching repositories'}
            description={
              repos.length === 0
                ? 'Clone a curated starter, browse Trending, or import any GitHub URL.'
                : 'Try clearing your search box or switching the license filter.'
            }
            actions={
              <HStack gap={2}>
                <Button label="Browse Trending" variant="primary" onClick={onNavigateTrending} />
                <Button label="Add by URL" variant="secondary" onClick={onNavigateAdd} />
              </HStack>
            }
          />
        ) : (
          <VStack gap={3}>
            {filtered.map((repo) => (
              <LocalRepoCard
                key={repo.path}
                repo={repo}
                syncing={Boolean(syncingMap[repo.path])}
                onInspectFiles={onInspectFiles}
                onReadReadme={onReadReadme}
                onAudit={onAudit}
                onOpenIde={onOpenIde}
                onSync={onSync}
                onDelete={onRequestDelete}
              />
            ))}
          </VStack>
        )}
      </VStack>
    </div>
  );
}
