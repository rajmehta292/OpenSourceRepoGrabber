import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import {
  BookOpen,
  Brain,
  Code2,
  Download,
  ExternalLink,
  FolderTree,
  GitFork,
  RefreshCw,
  Star,
  Trash2,
} from 'lucide-react';
import type { LocalRepo, RemoteRepo } from '../api/bridge';

export interface RemoteRepoCardProps {
  repo: RemoteRepo;
  cloning?: boolean;
  onOpenGitHub: (repo: RemoteRepo) => void;
  onPreviewReadme: (repo: RemoteRepo) => void;
  onClone: (repo: RemoteRepo) => void;
}

export function RemoteRepoCard({
  repo,
  cloning = false,
  onOpenGitHub,
  onPreviewReadme,
  onClone,
}: RemoteRepoCardProps) {
  const stars = (repo.stars ?? 0).toLocaleString();
  const forks = (repo.forks ?? 0).toLocaleString();
  const license = repo.license_spdx_id || 'Other';
  const language = repo.language || 'Unknown';

  return (
    <Card padding={4} variant="default">
      <HStack gap={4} justify="between" align="center" wrap="wrap">
        <VStack gap={1.5} style={{ flex: '1 1 380px', minWidth: 0 }}>
          <HStack gap={2} align="center" wrap="wrap">
            <Heading level={4}>{repo.full_name || repo.name}</Heading>
            {repo.difficulty && <Badge variant="green" label={repo.difficulty} />}
          </HStack>
          <Text color="secondary" maxLines={2}>
            {repo.description || 'No repository description available.'}
          </Text>
          {repo.why && (
            <Text size="sm" color="accent">
              Why start here: {repo.why}
            </Text>
          )}
          <HStack gap={2} align="center" wrap="wrap" style={{ marginTop: 4 }}>
            <Badge variant="neutral" icon={<Star size={12} />} label={stars} />
            {repo.forks !== undefined && (
              <Badge variant="neutral" icon={<GitFork size={12} />} label={forks} />
            )}
            <Badge variant="info" label={language} />
            <Badge variant="green" label={license} />
            {typeof repo.good_first_issues === 'number' && repo.good_first_issues > 0 && (
              <Badge variant="warning" label={`${repo.good_first_issues} beginner issues`} />
            )}
          </HStack>
        </VStack>

        <HStack gap={2} align="center" wrap="wrap" style={{ flexShrink: 0 }}>
          <Button
            label="GitHub"
            size="sm"
            variant="ghost"
            icon={<ExternalLink size={14} />}
            onClick={() => onOpenGitHub(repo)}
          />
          <Button
            label="Readme"
            size="sm"
            variant="secondary"
            icon={<BookOpen size={14} />}
            onClick={() => onPreviewReadme(repo)}
          />
          <Button
            label={cloning ? 'Cloning...' : 'Clone'}
            size="sm"
            variant="primary"
            isLoading={cloning}
            icon={<Download size={14} />}
            onClick={() => onClone(repo)}
          />
        </HStack>
      </HStack>
    </Card>
  );
}

export interface LocalRepoCardProps {
  repo: LocalRepo;
  syncing?: boolean;
  onInspectFiles: (repo: LocalRepo) => void;
  onReadReadme: (repo: LocalRepo) => void;
  onAudit: (repo: LocalRepo) => void;
  onOpenIde: (repo: LocalRepo) => void;
  onSync: (repo: LocalRepo) => void;
  onDelete: (repo: LocalRepo) => void;
}

export function LocalRepoCard({
  repo,
  syncing = false,
  onInspectFiles,
  onReadReadme,
  onAudit,
  onOpenIde,
  onSync,
  onDelete,
}: LocalRepoCardProps) {
  return (
    <Card padding={4} variant="default">
      <VStack gap={3}>
        <HStack justify="between" align="start" wrap="wrap" gap={3}>
          <VStack gap={1} style={{ flex: '1 1 360px', minWidth: 0 }}>
            <HStack gap={2} align="center" wrap="wrap">
              <Heading level={4}>{repo.full_name || repo.name}</Heading>
              <Badge variant="green" label={repo.license || 'Other'} />
            </HStack>
            <Text size="sm" color="secondary" type="code" maxLines={1}>
              {repo.path}
            </Text>
            {repo.last_commit && (
              <Text size="sm" color="secondary" maxLines={1}>
                Last commit: {repo.last_commit}
              </Text>
            )}
          </VStack>

          <HStack gap={2} wrap="wrap" align="center">
            <Button
              label="Code & Files"
              size="sm"
              variant="secondary"
              icon={<FolderTree size={14} />}
              onClick={() => onInspectFiles(repo)}
            />
            <Button
              label="README"
              size="sm"
              variant="ghost"
              icon={<BookOpen size={14} />}
              onClick={() => onReadReadme(repo)}
            />
            <Button
              label="Oracle Audit"
              size="sm"
              variant="secondary"
              icon={<Brain size={14} />}
              onClick={() => onAudit(repo)}
            />
            <Button
              label="Open IDE"
              size="sm"
              variant="primary"
              icon={<Code2 size={14} />}
              onClick={() => onOpenIde(repo)}
            />
            <Button
              label={syncing ? 'Syncing' : 'Pull'}
              size="sm"
              variant="ghost"
              isLoading={syncing}
              icon={<RefreshCw size={14} />}
              onClick={() => onSync(repo)}
            />
            <Button
              label="Delete"
              size="sm"
              variant="ghost"
              isIconOnly
              tooltip="Delete local clone"
              icon={<Trash2 size={14} />}
              onClick={() => onDelete(repo)}
            />
          </HStack>
        </HStack>

        {repo.smart_tags && repo.smart_tags.length > 0 && (
          <div className="osrg-chip-row">
            {repo.smart_tags.map((tag) => (
              <Badge key={tag} variant="neutral" label={tag} />
            ))}
          </div>
        )}
      </VStack>
    </Card>
  );
}
