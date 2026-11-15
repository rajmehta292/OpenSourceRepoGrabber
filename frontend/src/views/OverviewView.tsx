import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { Skeleton } from '@astryxdesign/core/Skeleton';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import {
  Brain,
  Code2,
  Flame,
  FolderGit2,
  FolderOpen,
  GraduationCap,
  PlusCircle,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react';
import type { OverviewData, RemoteRepo } from '../api/bridge';
import { RemoteRepoCard } from '../components/RepoCard';

export type NavTab =
  | 'overview'
  | 'repositories'
  | 'trending'
  | 'search'
  | 'launchpad'
  | 'add'
  | 'ai'
  | 'settings';

export interface OverviewViewProps {
  data: OverviewData | null;
  loading: boolean;
  cloningMap: Record<string, boolean>;
  onRefresh: () => void;
  onNavigate: (tab: NavTab) => void;
  onOpenExplorer: () => void;
  onOpenGitHub: (repo: RemoteRepo) => void;
  onPreviewReadme: (repo: RemoteRepo) => void;
  onClone: (repo: RemoteRepo) => void;
}

export function OverviewView({
  data,
  loading,
  cloningMap,
  onRefresh,
  onNavigate,
  onOpenExplorer,
  onOpenGitHub,
  onPreviewReadme,
  onClone,
}: OverviewViewProps) {
  const rate = data?.rate_limit;
  const ollama = data?.ollama;
  const starters = data?.starter_repos ?? [];

  return (
    <div className="osrg-page">
      <VStack gap={5}>
        <HStack justify="between" align="center" wrap="wrap" gap={3}>
          <VStack gap={1}>
            <Heading level={1}>OpenSource Discovery & Architecture Studio</Heading>
            <Text color="secondary">
              Explore trending repositories, inspect codebases in-app, decode licenses, and launch your first PR.
            </Text>
          </VStack>
          <HStack gap={2}>
            <Button
              label="Explore Trending"
              variant="primary"
              icon={<Flame size={15} />}
              onClick={() => onNavigate('trending')}
            />
            <Button
              label="Refresh Status"
              variant="secondary"
              isLoading={loading}
              icon={<RefreshCw size={15} />}
              onClick={onRefresh}
            />
          </HStack>
        </HStack>

        {rate && !rate.authenticated && rate.remaining < 20 && (
          <Banner
            status="warning"
            title={`Low Unauthenticated GitHub Quota (${rate.remaining}/${rate.limit})`}
            description="Add a Personal Access Token in Settings to raise your quota to 5,000 requests/hour."
            endContent={
              <Button label="Configure PAT" size="sm" variant="secondary" onClick={() => onNavigate('settings')} />
            }
          />
        )}

        {/* KPI Grid */}
        <div className="osrg-grid-4">
          <Card padding={4} variant="default">
            <VStack gap={1.5}>
              <Text size="sm" color="secondary">
                Cloned Libraries
              </Text>
              {loading && !data ? (
                <Skeleton height={32} width={80} />
              ) : (
                <Heading level={2}>{data?.local_count ?? 0}</Heading>
              )}
              <Button
                label="Browse Local"
                size="sm"
                variant="ghost"
                icon={<FolderGit2 size={14} />}
                onClick={() => onNavigate('repositories')}
              />
            </VStack>
          </Card>

          <Card padding={4} variant="default">
            <VStack gap={1.5}>
              <Text size="sm" color="secondary">
                GitHub API Quota
              </Text>
              {loading && !data ? (
                <Skeleton height={32} width={110} />
              ) : (
                <HStack gap={2} align="center">
                  <Heading level={2}>
                    {rate ? `${rate.remaining}/${rate.limit}` : '—'}
                  </Heading>
                  <Badge
                    variant={rate?.authenticated ? 'green' : 'neutral'}
                    label={rate?.authenticated ? 'PAT' : 'Guest'}
                  />
                </HStack>
              )}
              <Text size="sm" color="secondary">
                {rate?.reset_display ? `Resets at ${rate.reset_display}` : 'Cached status active'}
              </Text>
            </VStack>
          </Card>

          <Card padding={4} variant="default">
            <VStack gap={1.5}>
              <Text size="sm" color="secondary">
                Project Oracle AI
              </Text>
              {loading && !data ? (
                <Skeleton height={32} width={120} />
              ) : (
                <HStack gap={2} align="center">
                  <StatusDot
                    variant={ollama?.available ? 'success' : 'warning'}
                    label={ollama?.available ? 'Ollama connected' : 'Heuristic mode active'}
                  />
                  <Heading level={3}>
                    {ollama?.available ? 'Ollama Ready' : 'Heuristic Mode'}
                  </Heading>
                </HStack>
              )}
              <Text size="sm" color="secondary" maxLines={1}>
                {ollama?.available ? ollama.model : 'AST & pattern analysis ready offline'}
              </Text>
            </VStack>
          </Card>

          <Card padding={4} variant="default">
            <VStack gap={1.5}>
              <Text size="sm" color="secondary">
                Workspace Root
              </Text>
              <Text type="code" size="sm" maxLines={2}>
                {data?.repos_path || 'Loading...'}
              </Text>
              <Button
                label="Open Folder"
                size="sm"
                variant="ghost"
                icon={<FolderOpen size={14} />}
                onClick={onOpenExplorer}
              />
            </VStack>
          </Card>
        </div>

        {/* 3 Core Personas */}
        <VStack gap={3}>
          <Heading level={3}>Built for Every Kind of Developer</Heading>
          <div className="osrg-grid-3">
            <Card padding={4} variant="green">
              <VStack gap={2}>
                <HStack gap={2} align="center">
                  <Code2 size={18} />
                  <Heading level={4}>The Tinkerer</Heading>
                </HStack>
                <Text color="secondary">
                  Preview remote READMEs, inspect local file trees with syntax highlighting, and clone starter sandboxes in one click.
                </Text>
                <HStack gap={2}>
                  <Button label="Trending" size="sm" variant="secondary" onClick={() => onNavigate('trending')} />
                  <Button label="Search GitHub" size="sm" variant="ghost" icon={<Search size={14} />} onClick={() => onNavigate('search')} />
                </HStack>
              </VStack>
            </Card>

            <Card padding={4} variant="default">
              <VStack gap={2}>
                <HStack gap={2} align="center">
                  <Brain size={18} />
                  <Heading level={4}>The Builder & Architect</Heading>
                </HStack>
                <Text color="secondary">
                  Run automated AST + LLM architectural audits, smart-tag local repositories by SPDX license, and launch your IDE directly.
                </Text>
                <HStack gap={2}>
                  <Button label="Local Repos" size="sm" variant="secondary" onClick={() => onNavigate('repositories')} />
                  <Button label="AI Explain" size="sm" variant="ghost" icon={<Sparkles size={14} />} onClick={() => onNavigate('ai')} />
                </HStack>
              </VStack>
            </Card>

            <Card padding={4} variant="default">
              <VStack gap={2}>
                <HStack gap={2} align="center">
                  <GraduationCap size={18} />
                  <Heading level={4}>The OSS Learner</Heading>
                </HStack>
                <Text color="secondary">
                  Discover real "good first issues", decode open-source license obligations, and track your first Pull Request step-by-step.
                </Text>
                <HStack gap={2}>
                  <Button label="OSS Launchpad" size="sm" variant="secondary" onClick={() => onNavigate('launchpad')} />
                  <Button label="Add by URL" size="sm" variant="ghost" icon={<PlusCircle size={14} />} onClick={() => onNavigate('add')} />
                </HStack>
              </VStack>
            </Card>
          </div>
        </VStack>

        {/* Curated Starter Repositories */}
        <VStack gap={3}>
          <HStack justify="between" align="center" wrap="wrap" gap={2}>
            <VStack gap={0.5}>
              <Heading level={3}>Curated Starter Kits & Sandboxes</Heading>
              <Text size="sm" color="secondary">
                Beginner-friendly and architecture-exemplar repositories ready to preview or clone.
              </Text>
            </VStack>
            <Button label="Find More in Search" size="sm" variant="ghost" onClick={() => onNavigate('search')} />
          </HStack>

          <VStack gap={3}>
            {starters.map((repo) => (
              <RemoteRepoCard
                key={repo.full_name}
                repo={repo}
                cloning={Boolean(cloningMap[repo.full_name])}
                onOpenGitHub={onOpenGitHub}
                onPreviewReadme={onPreviewReadme}
                onClone={onClone}
              />
            ))}
          </VStack>
        </VStack>
      </VStack>
    </div>
  );
}
