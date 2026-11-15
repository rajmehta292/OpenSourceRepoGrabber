import { useState } from 'react';
import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { Selector } from '@astryxdesign/core/Selector';
import { Spinner } from '@astryxdesign/core/Spinner';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { VStack } from '@astryxdesign/core/VStack';
import { Flame, RefreshCw, Search } from 'lucide-react';
import type { RemoteRepo } from '../api/bridge';
import { RemoteRepoCard } from '../components/RepoCard';

const TRENDING_LANGUAGES = [
  { label: 'All Languages', value: '' },
  { label: 'Python', value: 'Python' },
  { label: 'TypeScript', value: 'TypeScript' },
  { label: 'JavaScript', value: 'JavaScript' },
  { label: 'Rust', value: 'Rust' },
  { label: 'Go', value: 'Go' },
  { label: 'C++', value: 'C++' },
  { label: 'Shell', value: 'Shell' },
];

const QUICK_TOPICS = [
  'FastAPI',
  'React',
  'Rust',
  'LLM & AI',
  'CLI Tools',
  'Go',
  'Docker',
  'Next.js',
];

const SEARCH_LANGUAGES = ['All', 'Python', 'TypeScript', 'JavaScript', 'Rust', 'Go', 'C++', 'Java'];

export interface TrendingViewProps {
  items: RemoteRepo[];
  language: string;
  loading: boolean;
  cloningMap: Record<string, boolean>;
  onSelectLanguage: (lang: string) => void;
  onRefresh: () => void;
  onOpenGitHub: (repo: RemoteRepo) => void;
  onPreviewReadme: (repo: RemoteRepo) => void;
  onClone: (repo: RemoteRepo) => void;
}

export function TrendingView({
  items,
  language,
  loading,
  cloningMap,
  onSelectLanguage,
  onRefresh,
  onOpenGitHub,
  onPreviewReadme,
  onClone,
}: TrendingViewProps) {
  return (
    <div className="osrg-page">
      <VStack gap={4}>
        <HStack justify="between" align="center" wrap="wrap" gap={3}>
          <VStack gap={1}>
            <HStack gap={2} align="center">
              <Heading level={1}>Trending Repositories</Heading>
              <Badge variant="green" label={`${items.length} active`} />
            </HStack>
            <Text color="secondary">
              High-momentum open-source repositories — GPU-accelerated scroll with instant cache switching.
            </Text>
          </VStack>

          <Button
            label="Force Refresh"
            size="sm"
            variant="secondary"
            isLoading={loading}
            icon={<RefreshCw size={14} />}
            onClick={onRefresh}
          />
        </HStack>

        <div className="osrg-chip-row">
          {TRENDING_LANGUAGES.map((lang) => (
            <button
              key={lang.label}
              type="button"
              className="osrg-filter-pill"
              data-active={language === lang.value}
              onClick={() => onSelectLanguage(lang.value)}
            >
              {lang.label}
            </button>
          ))}
        </div>

        {loading && items.length === 0 ? (
          <HStack gap={2} align="center" style={{ padding: '48px 8px' }}>
            <Spinner size="md" />
            <Text color="secondary">Fetching trending repositories from GitHub...</Text>
          </HStack>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Flame size={36} />}
            title="No trending repositories loaded"
            description="Check your network connection or GitHub rate limit, then hit Force Refresh."
            actions={<Button label="Retry Load" variant="primary" onClick={onRefresh} />}
          />
        ) : (
          <VStack gap={3}>
            {items.map((repo) => (
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
        )}
      </VStack>
    </div>
  );
}

export interface SearchViewProps {
  query: string;
  language: string;
  items: RemoteRepo[];
  loading: boolean;
  hasSearched: boolean;
  cloningMap: Record<string, boolean>;
  onSearch: (query: string, language: string) => void;
  onOpenGitHub: (repo: RemoteRepo) => void;
  onPreviewReadme: (repo: RemoteRepo) => void;
  onClone: (repo: RemoteRepo) => void;
}

export function SearchView({
  query: initialQuery,
  language: initialLanguage,
  items,
  loading,
  hasSearched,
  cloningMap,
  onSearch,
  onOpenGitHub,
  onPreviewReadme,
  onClone,
}: SearchViewProps) {
  const [draftQuery, setDraftQuery] = useState(initialQuery);
  const [selectedLang, setSelectedLang] = useState(initialLanguage || 'All');

  const triggerSearch = (q = draftQuery, lang = selectedLang) => {
    setDraftQuery(q);
    setSelectedLang(lang);
    onSearch(q, lang);
  };

  return (
    <div className="osrg-page">
      <VStack gap={4}>
        <VStack gap={1}>
          <Heading level={1}>Explore & Search GitHub</Heading>
          <Text color="secondary">
            Search across millions of public repositories by keyword, stack, or quick topic.
          </Text>
        </VStack>

        <HStack gap={3} align="end" wrap="wrap">
          <div style={{ flex: '1 1 320px' }}>
            <TextInput
              label="Search query"
              placeholder="e.g. fastapi template, rust tui, local llm..."
              hasClear
              value={draftQuery}
              onChange={setDraftQuery}
              onEnter={() => triggerSearch(draftQuery, selectedLang)}
            />
          </div>
          <div style={{ width: 170 }}>
            <Selector
              label="Language"
              value={selectedLang}
              options={SEARCH_LANGUAGES}
              onChange={(val) => {
                setSelectedLang(val);
                if (draftQuery.trim()) {
                  triggerSearch(draftQuery, val);
                }
              }}
            />
          </div>
          <Button
            label={loading ? 'Searching...' : 'Search'}
            variant="primary"
            isLoading={loading}
            icon={<Search size={15} />}
            onClick={() => triggerSearch(draftQuery, selectedLang)}
          />
        </HStack>

        <div className="osrg-chip-row">
          <Text size="sm" color="secondary">
            Quick topics:
          </Text>
          {QUICK_TOPICS.map((topic) => (
            <button
              key={topic}
              type="button"
              className="osrg-filter-pill"
              data-active={draftQuery.toLowerCase() === topic.toLowerCase()}
              onClick={() => triggerSearch(topic, selectedLang)}
            >
              {topic}
            </button>
          ))}
        </div>

        {loading ? (
          <HStack gap={2} align="center" style={{ padding: '48px 8px' }}>
            <Spinner size="md" />
            <Text color="secondary">Searching repositories...</Text>
          </HStack>
        ) : !hasSearched ? (
          <EmptyState
            icon={<Search size={36} />}
            title="Pick a topic or enter a query"
            description="Press Enter or click one of the quick topic pills above to discover projects immediately."
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Search size={36} />}
            title="No repositories found"
            description="Try broader keywords or set the Language filter back to All."
          />
        ) : (
          <VStack gap={3}>
            <Text size="sm" color="secondary">
              Showing {items.length} results for "{initialQuery}"
            </Text>
            {items.map((repo) => (
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
        )}
      </VStack>
    </div>
  );
}
