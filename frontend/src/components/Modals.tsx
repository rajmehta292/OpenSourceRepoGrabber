import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { CodeBlock } from '@astryxdesign/core/CodeBlock';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { HStack } from '@astryxdesign/core/HStack';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Spinner } from '@astryxdesign/core/Spinner';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { VStack } from '@astryxdesign/core/VStack';
import {
  Brain,
  Copy,
  Download,
  ExternalLink,
  FileCode2,
  FolderOpen,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { getBridge } from '../api/bridge';

function inferLanguage(path: string): string {
  const lower = path.toLowerCase();
  const ext = lower.includes('.') ? lower.split('.').pop() || '' : '';
  const map: Record<string, string> = {
    py: 'python',
    ts: 'typescript',
    tsx: 'tsx',
    js: 'javascript',
    jsx: 'jsx',
    json: 'json',
    md: 'markdown',
    yml: 'yaml',
    yaml: 'yaml',
    rs: 'rust',
    go: 'go',
    cs: 'csharp',
    css: 'css',
    html: 'html',
    sh: 'bash',
    bash: 'bash',
    sql: 'sql',
    toml: 'toml',
  };
  return map[ext] || 'plaintext';
}

export interface ReadmeModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content: string;
  loading?: boolean;
  githubUrl?: string;
  onClone?: () => void;
  cloning?: boolean;
}

export function ReadmeDialog({
  isOpen,
  onClose,
  title,
  content,
  loading = false,
  githubUrl,
  onClone,
  cloning = false,
}: ReadmeModalProps) {
  return (
    <Dialog isOpen={isOpen} onOpenChange={(open) => !open && onClose()} width={860} maxHeight="84dvh">
      <VStack gap={3} style={{ height: '100%' }}>
        <DialogHeader
          title={`README — ${title}`}
          subtitle="Rendered offline inside OSRG"
          onOpenChange={(open) => !open && onClose()}
          endContent={
            <HStack gap={2}>
              {githubUrl && (
                <Button
                  label="GitHub"
                  size="sm"
                  variant="ghost"
                  icon={<ExternalLink size={14} />}
                  onClick={async () => {
                    const api = await getBridge();
                    await api.open_external_url(githubUrl);
                  }}
                />
              )}
              {onClone && (
                <Button
                  label={cloning ? 'Cloning...' : 'Clone Repo'}
                  size="sm"
                  variant="primary"
                  isLoading={cloning}
                  icon={<Download size={14} />}
                  onClick={onClone}
                />
              )}
            </HStack>
          }
        />

        <div style={{ overflowY: 'auto', padding: '4px 4px 12px', flex: 1 }}>
          {loading ? (
            <HStack gap={2} align="center" style={{ padding: '40px 16px' }}>
              <Spinner size="md" />
              <Text color="secondary">Fetching README content...</Text>
            </HStack>
          ) : content ? (
            <Markdown
              contentWidth="100%"
              onLinkClick={(href) => {
                void getBridge().then((api) => api.open_external_url(href));
                return false;
              }}
            >
              {content}
            </Markdown>
          ) : (
            <Banner status="info" title="No README found" description="This repository did not return a README file." />
          )}
        </div>
      </VStack>
    </Dialog>
  );
}

export interface FileExplorerModalProps {
  isOpen: boolean;
  onClose: () => void;
  repoName: string;
  repoPath: string;
}

export function FileExplorerDialog({
  isOpen,
  onClose,
  repoName,
  repoPath,
}: FileExplorerModalProps) {
  const [files, setFiles] = useState<string[]>([]);
  const [stats, setStats] = useState<{ files?: number; dirs?: number; size_mb?: number }>({});
  const [loadingTree, setLoadingTree] = useState(false);
  const [filter, setFilter] = useState('');
  const [selectedFile, setSelectedFile] = useState('');
  const [fileContent, setFileContent] = useState('');
  const [fileError, setFileError] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);

  useEffect(() => {
    if (!isOpen || !repoPath) return;
    setLoadingTree(true);
    setSelectedFile('');
    setFileContent('');
    setFileError('');
    setFilter('');
    void getBridge()
      .then((api) => api.get_local_file_tree(repoPath, 300))
      .then((res) => {
        if (res.ok) {
          setFiles(res.files || []);
          setStats(res.stats || {});
          const preferred =
            (res.files || []).find((f) => f.toLowerCase() === 'readme.md') ||
            (res.files || []).find((f) => f.endsWith('.py') || f.endsWith('.ts') || f.endsWith('.tsx')) ||
            res.files?.[0] ||
            '';
          if (preferred) {
            void loadFile(preferred);
          }
        }
      })
      .finally(() => setLoadingTree(false));
  }, [isOpen, repoPath]);

  const loadFile = async (relPath: string) => {
    setSelectedFile(relPath);
    setLoadingFile(true);
    setFileError('');
    try {
      const api = await getBridge();
      const res = await api.read_local_file(repoPath, relPath);
      if (res.ok) {
        setFileContent(res.content || '');
      } else {
        setFileContent('');
        setFileError(res.error || 'Could not read file.');
      }
    } catch (e) {
      setFileError(String(e));
    } finally {
      setLoadingFile(false);
    }
  };

  const filteredFiles = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return files;
    return files.filter((f) => f.toLowerCase().includes(q));
  }, [files, filter]);

  return (
    <Dialog isOpen={isOpen} onOpenChange={(open) => !open && onClose()} width={1040} maxHeight="88dvh">
      <VStack gap={3}>
        <DialogHeader
          title={`File Inspector — ${repoName}`}
          subtitle={`${stats.files ?? files.length} files · ${stats.dirs ?? 0} folders · ${stats.size_mb ?? 0} MB`}
          onOpenChange={(open) => !open && onClose()}
          endContent={
            <HStack gap={2}>
              <Button
                label="Open Folder"
                size="sm"
                variant="ghost"
                icon={<FolderOpen size={14} />}
                onClick={async () => {
                  const api = await getBridge();
                  await api.open_in_explorer(repoPath);
                }}
              />
              <Button
                label="Open in IDE"
                size="sm"
                variant="secondary"
                onClick={async () => {
                  const api = await getBridge();
                  await api.open_in_editor(repoPath, 'auto');
                }}
              />
            </HStack>
          }
        />

        {loadingTree ? (
          <HStack gap={2} align="center" style={{ padding: '40px 16px' }}>
            <Spinner size="md" />
            <Text color="secondary">Indexing files...</Text>
          </HStack>
        ) : (
          <div className="osrg-file-split">
            <VStack gap={2} style={{ minHeight: 0 }}>
              <TextInput
                label="Filter files"
                isLabelHidden
                size="sm"
                hasClear
                placeholder="Filter path (e.g. .py, config)..."
                value={filter}
                onChange={setFilter}
              />
              <div className="osrg-file-list" style={{ flex: 1 }}>
                {filteredFiles.map((rel) => (
                  <button
                    key={rel}
                    type="button"
                    className="osrg-file-btn"
                    data-active={selectedFile === rel}
                    onClick={() => void loadFile(rel)}
                  >
                    <FileCode2 size={14} style={{ flexShrink: 0, opacity: 0.7 }} />
                    <span>{rel}</span>
                  </button>
                ))}
                {filteredFiles.length === 0 && (
                  <Text size="sm" color="secondary" style={{ padding: '12px' }}>
                    No files match "{filter}".
                  </Text>
                )}
              </div>
            </VStack>

            <div className="osrg-code-pane">
              {loadingFile ? (
                <HStack gap={2} align="center" style={{ padding: '24px' }}>
                  <Spinner size="sm" />
                  <Text color="secondary">Loading {selectedFile}...</Text>
                </HStack>
              ) : fileError ? (
                <Banner status="warning" title="Preview unavailable" description={fileError} />
              ) : selectedFile ? (
                <CodeBlock
                  title={selectedFile}
                  code={fileContent || '// Empty file'}
                  language={inferLanguage(selectedFile)}
                  hasLineNumbers
                  hasCopyButton
                  width="100%"
                  maxHeight="58dvh"
                />
              ) : (
                <Banner status="info" title="Select a file" description="Choose any file on the left to inspect its source code instantly." />
              )}
            </div>
          </div>
        )}
      </VStack>
    </Dialog>
  );
}

export interface AuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  repoName: string;
  repoPath: string;
  fullName: string;
}

export function AuditDialog({
  isOpen,
  onClose,
  repoName,
  repoPath,
  fullName,
}: AuditModalProps) {
  const [report, setReport] = useState('');
  const [smartTags, setSmartTags] = useState<string[]>([]);
  const [cached, setCached] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runAudit = async (force: boolean) => {
    setLoading(true);
    setError('');
    try {
      const api = await getBridge();
      const res = await api.run_architectural_audit(repoPath, fullName, force);
      if (res.ok) {
        setReport(res.report || '');
        setSmartTags(res.smart_tags || []);
        setCached(Boolean(res.cached));
      } else {
        setError(res.error || 'Architectural audit failed.');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && repoPath) {
      void runAudit(false);
    }
  }, [isOpen, repoPath]);

  return (
    <Dialog isOpen={isOpen} onOpenChange={(open) => !open && onClose()} width={860} maxHeight="84dvh">
      <VStack gap={3}>
        <DialogHeader
          title={`Project Oracle Audit — ${repoName}`}
          subtitle={cached ? 'Loaded cached architectural synthesis' : 'Fresh structural & AST analysis'}
          onOpenChange={(open) => !open && onClose()}
          endContent={
            <HStack gap={2}>
              {report && (
                <Button
                  label="Copy Report"
                  size="sm"
                  variant="ghost"
                  icon={<Copy size={14} />}
                  onClick={() => void navigator.clipboard.writeText(report)}
                />
              )}
              <Button
                label="Re-Run"
                size="sm"
                variant="secondary"
                isLoading={loading}
                icon={<RefreshCw size={14} />}
                onClick={() => void runAudit(true)}
              />
            </HStack>
          }
        />

        {smartTags.length > 0 && (
          <div className="osrg-chip-row">
            {smartTags.map((tag) => (
              <Badge key={tag} variant="green" label={tag} />
            ))}
          </div>
        )}

        <div style={{ overflowY: 'auto', maxHeight: '62dvh', paddingRight: '4px' }}>
          {loading ? (
            <HStack gap={2} align="center" style={{ padding: '40px 12px' }}>
              <Spinner size="md" />
              <Brain size={18} />
              <Text color="secondary">Analyzing codebase topology & AST dependencies...</Text>
            </HStack>
          ) : error ? (
            <Banner status="error" title="Audit Failed" description={error} />
          ) : (
            <Markdown
              contentWidth="100%"
              onLinkClick={(href) => {
                void getBridge().then((api) => api.open_external_url(href));
                return false;
              }}
            >
              {report}
            </Markdown>
          )}
        </div>
      </VStack>
    </Dialog>
  );
}

export interface ConfirmDeleteProps {
  isOpen: boolean;
  repoName: string;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDeleteDialog({
  isOpen,
  repoName,
  deleting,
  onCancel,
  onConfirm,
}: ConfirmDeleteProps) {
  return (
    <Dialog isOpen={isOpen} onOpenChange={(open) => !open && onCancel()} width={460}>
      <VStack gap={4}>
        <DialogHeader
          title="Delete Local Repository"
          subtitle="Removes cloned files from disk"
          onOpenChange={(open) => !open && onCancel()}
        />
        <Text>
          Permanently remove <strong>{repoName}</strong> from your local workspace? GitHub remote is untouched.
        </Text>
        <HStack gap={2} justify="end">
          <Button label="Cancel" variant="ghost" onClick={onCancel} isDisabled={deleting} />
          <Button
            label={deleting ? 'Deleting...' : 'Delete Folder'}
            variant="destructive"
            icon={<Trash2 size={14} />}
            isLoading={deleting}
            onClick={onConfirm}
          />
        </HStack>
      </VStack>
    </Dialog>
  );
}
