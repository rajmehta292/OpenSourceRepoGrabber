import { useState } from 'react';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Selector } from '@astryxdesign/core/Selector';
import { Spinner } from '@astryxdesign/core/Spinner';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Text } from '@astryxdesign/core/Text';
import { TextArea } from '@astryxdesign/core/TextArea';
import { TextInput } from '@astryxdesign/core/TextInput';
import { VStack } from '@astryxdesign/core/VStack';
import { Brain, Copy, Download, FolderOpen, KeyRound, RefreshCw, Sparkles } from 'lucide-react';
import { getBridge, type LocalRepo, type RateLimitInfo } from '../api/bridge';

const LICENSE_OVERRIDE_OPTIONS = [
  'Auto-detect from GitHub',
  'MIT',
  'Apache-2.0',
  'GPL-3.0',
  'BSD-3-Clause',
  'MPL-2.0',
  'ISC',
  'Other',
];

export interface AddRepoViewProps {
  onCloned: (result: LocalRepo) => void;
}

export function AddRepoView({ onCloned }: AddRepoViewProps) {
  const [urlInput, setUrlInput] = useState('');
  const [licenseChoice, setLicenseChoice] = useState('Auto-detect from GitHub');
  const [cloning, setCloning] = useState(false);
  const [error, setError] = useState('');
  const [clonedResult, setClonedResult] = useState<(LocalRepo & { status: string }) | null>(null);

  const handleSubmit = async () => {
    const cleaned = urlInput.trim();
    if (!cleaned) {
      setError('Enter a GitHub URL (https://github.com/owner/repo) or owner/repo.');
      return;
    }
    setCloning(true);
    setError('');
    setClonedResult(null);
    try {
      const api = await getBridge();
      const spdx = licenseChoice === 'Auto-detect from GitHub' ? null : licenseChoice;
      const res = await api.clone_repo(cleaned, spdx);
      if (res.ok && res.result) {
        setClonedResult(res.result);
        setUrlInput('');
        onCloned(res.result);
      } else {
        setError(res.error || 'Repository clone failed.');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setCloning(false);
    }
  };

  return (
    <div className="osrg-page">
      <VStack gap={4} style={{ maxWidth: 780 }}>
        <VStack gap={1}>
          <Heading level={1}>Add Repository to Local Workspace</Heading>
          <Text color="secondary">
            Clone any GitHub repository automatically sorted into its SPDX license directory, with smart tags generated on arrival.
          </Text>
        </VStack>

        <Card padding={5} variant="default">
          <VStack gap={4}>
            <TextInput
              label="GitHub URL or owner/repo"
              description="Accepts full URLs (https://github.com/fastapi/fastapi) or shorthand (tiangolo/sqlmodel)."
              placeholder="owner/repo or https://github.com/owner/repo"
              value={urlInput}
              hasClear
              onChange={setUrlInput}
              onEnter={() => void handleSubmit()}
            />

            <Selector
              label="License Folder Override"
              options={LICENSE_OVERRIDE_OPTIONS}
              value={licenseChoice}
              onChange={setLicenseChoice}
            />

            <HStack gap={2} align="center">
              <Button
                label={cloning ? 'Cloning Repository...' : 'Clone & Analyze'}
                variant="primary"
                isLoading={cloning}
                icon={<Download size={15} />}
                onClick={() => void handleSubmit()}
              />
            </HStack>

            {error && <Banner status="error" title="Clone Failed" description={error} />}

            {clonedResult && (
              <Banner
                status="success"
                title={`Ready: ${clonedResult.full_name || clonedResult.name}`}
                description={`Sorted under ${clonedResult.license} at ${clonedResult.path}`}
              >
                {clonedResult.smart_tags && clonedResult.smart_tags.length > 0 && (
                  <div className="osrg-chip-row" style={{ marginTop: 8 }}>
                    {clonedResult.smart_tags.map((tag) => (
                      <Badge key={tag} variant="green" label={tag} />
                    ))}
                  </div>
                )}
              </Banner>
            )}
          </VStack>
        </Card>
      </VStack>
    </div>
  );
}

const AI_PROMPTS = [
  {
    label: 'Explain FastAPI Dependency Injection',
    prompt: `from fastapi import Depends, FastAPI\n\napp = FastAPI()\n\ndef get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n\n@app.get('/items')\ndef read_items(db = Depends(get_db)):\n    return db.query(Item).all()`,
  },
  {
    label: 'Review React Effect Hook',
    prompt: `useEffect(() => {\n  const id = setInterval(() => setCount((c) => c + 1), 1000);\n  return () => clearInterval(id);\n}, []);`,
  },
  {
    label: 'Audit SQLite Connection Pattern',
    prompt: `import sqlite3\n\ndef query_users(name):\n    conn = sqlite3.connect('app.db')\n    return conn.execute("SELECT * FROM users WHERE name = '" + name + "'").fetchall()`,
  },
];

export interface AiExplainViewProps {
  available: boolean;
  models: string[];
  currentModel: string;
  onRefreshModels: () => void;
  onSelectModel: (model: string) => void;
}

export function AiExplainView({
  available,
  models,
  currentModel,
  onRefreshModels,
  onSelectModel,
}: AiExplainViewProps) {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('Auto-detect');
  const [analysis, setAnalysis] = useState('');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  const handleAnalyze = async () => {
    if (!code.trim()) {
      setError('Paste a snippet of code or an architecture question first.');
      return;
    }
    setRunning(true);
    setError('');
    try {
      const api = await getBridge();
      const langArg = language === 'Auto-detect' ? null : language;
      const res = await api.analyze_code(code, langArg);
      if (res.ok && res.analysis) {
        setAnalysis(res.analysis);
      } else {
        setError(res.error || 'Analysis failed.');
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="osrg-page">
      <VStack gap={4}>
        <HStack justify="between" align="center" wrap="wrap" gap={3}>
          <VStack gap={1}>
            <HStack gap={2} align="center">
              <Heading level={1}>AI Code Explainer & Oracle</Heading>
              <HStack gap={1.5} align="center">
                <StatusDot
                  variant={available ? 'success' : 'warning'}
                  label={available ? 'Ollama connected' : 'Heuristic engine active'}
                />
                <Badge
                  variant={available ? 'green' : 'warning'}
                  label={available ? 'Ollama Connected' : 'Heuristic Engine Active'}
                />
              </HStack>
            </HStack>
            <Text color="secondary">
              Runs deep local LLM analysis via Ollama when available, or resilient AST/pattern synthesis offline.
            </Text>
          </VStack>

          <HStack gap={2} align="end">
            {models.length > 0 && (
              <div style={{ width: 220 }}>
                <Selector
                  label="Model"
                  size="sm"
                  value={currentModel}
                  options={models}
                  onChange={onSelectModel}
                />
              </div>
            )}
            <Button
              label="Refresh Ollama"
              size="sm"
              variant="secondary"
              icon={<RefreshCw size={14} />}
              onClick={onRefreshModels}
            />
          </HStack>
        </HStack>

        <div className="osrg-chip-row">
          <Text size="sm" color="secondary">
            Sample snippets:
          </Text>
          {AI_PROMPTS.map((sample) => (
            <button
              key={sample.label}
              type="button"
              className="osrg-filter-pill"
              onClick={() => setCode(sample.prompt)}
            >
              {sample.label}
            </button>
          ))}
        </div>

        <Card padding={4} variant="default">
          <VStack gap={3}>
            <HStack gap={3} align="end" justify="between" wrap="wrap">
              <div style={{ width: 200 }}>
                <Selector
                  label="Language Hint"
                  size="sm"
                  value={language}
                  options={['Auto-detect', 'Python', 'TypeScript', 'JavaScript', 'Rust', 'Go', 'C++', 'SQL']}
                  onChange={setLanguage}
                />
              </div>
              <Button
                label={running ? 'Analyzing...' : 'Explain & Audit Snippet'}
                variant="primary"
                isLoading={running}
                icon={<Sparkles size={15} />}
                onClick={() => void handleAnalyze()}
              />
            </HStack>

            <TextArea
              label="Code snippet or technical question"
              rows={9}
              placeholder="Paste any function, config, stack trace, or codebase snippet..."
              value={code}
              onChange={setCode}
            />
          </VStack>
        </Card>

        {error && <Banner status="error" title="Analysis Error" description={error} />}

        {running && (
          <HStack gap={2} align="center" style={{ padding: '16px 4px' }}>
            <Spinner size="md" />
            <Brain size={18} />
            <Text color="secondary">Synthesizing explanation...</Text>
          </HStack>
        )}

        {analysis && !running && (
          <Card padding={5} variant="default">
            <VStack gap={3}>
              <HStack justify="between" align="center">
                <Heading level={3}>Oracle Analysis</Heading>
                <Button
                  label="Copy"
                  size="sm"
                  variant="ghost"
                  icon={<Copy size={14} />}
                  onClick={() => void navigator.clipboard.writeText(analysis)}
                />
              </HStack>
              <Markdown
                contentWidth="100%"
                onLinkClick={(href) => {
                  void getBridge().then((api) => api.open_external_url(href));
                  return false;
                }}
              >
                {analysis}
              </Markdown>
            </VStack>
          </Card>
        )}
      </VStack>
    </div>
  );
}

export interface SettingsViewProps {
  reposPath: string;
  hasToken: boolean;
  rateLimit: RateLimitInfo | null;
  ollamaUrl: string;
  onTokenSaved: (rate: RateLimitInfo) => void;
  onOllamaUrlSaved: () => void;
  onOpenStorageFolder: () => void;
}

export function SettingsView({
  reposPath,
  hasToken,
  rateLimit,
  ollamaUrl: initialOllamaUrl,
  onTokenSaved,
  onOllamaUrlSaved,
  onOpenStorageFolder,
}: SettingsViewProps) {
  const [tokenInput, setTokenInput] = useState('');
  const [savingToken, setSavingToken] = useState(false);
  const [tokenMsg, setTokenMsg] = useState<{ status: 'success' | 'error'; text: string } | null>(null);

  const [ollamaInput, setOllamaInput] = useState(initialOllamaUrl || 'http://localhost:11434');
  const [savingOllama, setSavingOllama] = useState(false);
  const [ollamaMsg, setOllamaMsg] = useState<{ status: 'success' | 'error'; text: string } | null>(null);

  const handleSaveToken = async () => {
    setSavingToken(true);
    setTokenMsg(null);
    try {
      const api = await getBridge();
      const res = await api.set_github_token(tokenInput);
      if (res.ok && res.rate_limit) {
        onTokenSaved(res.rate_limit);
        setTokenMsg({
          status: 'success',
          text: `Token updated. Quota: ${res.rate_limit.remaining}/${res.rate_limit.limit}`,
        });
        setTokenInput('');
      } else {
        setTokenMsg({ status: 'error', text: res.error || 'Could not update token.' });
      }
    } catch (e) {
      setTokenMsg({ status: 'error', text: String(e) });
    } finally {
      setSavingToken(false);
    }
  };

  const handleSaveOllama = async () => {
    setSavingOllama(true);
    setOllamaMsg(null);
    try {
      const api = await getBridge();
      const res = await api.set_ollama_url(ollamaInput);
      if (res.ok) {
        onOllamaUrlSaved();
        setOllamaMsg({
          status: 'success',
          text: res.available
            ? `Connected! Found ${res.models.length} local model(s).`
            : 'Endpoint updated. Ollama server not currently responding (heuristic fallback remains active).',
        });
      } else {
        setOllamaMsg({ status: 'error', text: res.error || 'Failed to update endpoint.' });
      }
    } catch (e) {
      setOllamaMsg({ status: 'error', text: String(e) });
    } finally {
      setSavingOllama(false);
    }
  };

  return (
    <div className="osrg-page">
      <VStack gap={4} style={{ maxWidth: 820 }}>
        <VStack gap={1}>
          <Heading level={1}>Settings & Credentials</Heading>
          <Text color="secondary">
            Manage GitHub Personal Access Tokens, local clone directories, and local Ollama AI integration.
          </Text>
        </VStack>

        <Card padding={5} variant="default">
          <VStack gap={3}>
            <HStack justify="between" align="center" wrap="wrap" gap={2}>
              <HStack gap={2} align="center">
                <KeyRound size={18} />
                <Heading level={3}>GitHub Personal Access Token (PAT)</Heading>
              </HStack>
              <Badge
                variant={hasToken ? 'green' : 'neutral'}
                label={hasToken ? 'Token Configured (5,000/hr)' : 'Unauthenticated (60/hr)'}
              />
            </HStack>

            {rateLimit && (
              <Text size="sm" color="secondary">
                Current Quota: {rateLimit.remaining} / {rateLimit.limit} remaining
                {rateLimit.reset_display ? ` · Resets at ${rateLimit.reset_display}` : ''}
              </Text>
            )}

            <TextInput
              type="password"
              label="GitHub Token (session or stored)"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              value={tokenInput}
              onChange={setTokenInput}
              onEnter={() => void handleSaveToken()}
            />

            <HStack gap={2}>
              <Button
                label={savingToken ? 'Verifying...' : 'Apply & Verify Quota'}
                variant="primary"
                isLoading={savingToken}
                onClick={() => void handleSaveToken()}
              />
              <Button
                label="Clear Token"
                variant="ghost"
                onClick={() => {
                  setTokenInput('');
                  void getBridge().then(async (api) => {
                    const res = await api.set_github_token('');
                    if (res.ok && res.rate_limit) onTokenSaved(res.rate_limit);
                  });
                }}
              />
            </HStack>

            {tokenMsg && <Banner status={tokenMsg.status} title={tokenMsg.text} />}
          </VStack>
        </Card>

        <Card padding={5} variant="default">
          <VStack gap={3}>
            <Heading level={3}>Local Storage Root</Heading>
            <Text type="code" size="sm">
              {reposPath || 'Loading...'}
            </Text>
            <HStack gap={2}>
              <Button
                label="Open Workspace in File Explorer"
                variant="secondary"
                icon={<FolderOpen size={15} />}
                onClick={onOpenStorageFolder}
              />
            </HStack>
          </VStack>
        </Card>

        <Card padding={5} variant="default">
          <VStack gap={3}>
            <Heading level={3}>Ollama Local Inference Endpoint</Heading>
            <TextInput
              label="Ollama Server URL"
              value={ollamaInput}
              onChange={setOllamaInput}
              onEnter={() => void handleSaveOllama()}
            />
            <HStack gap={2}>
              <Button
                label={savingOllama ? 'Testing...' : 'Save & Test Connection'}
                variant="secondary"
                isLoading={savingOllama}
                onClick={() => void handleSaveOllama()}
              />
            </HStack>
            {ollamaMsg && <Banner status={ollamaMsg.status} title={ollamaMsg.text} />}
          </VStack>
        </Card>
      </VStack>
    </div>
  );
}
