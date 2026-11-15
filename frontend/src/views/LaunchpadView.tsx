import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { CheckboxList, CheckboxListItem } from '@astryxdesign/core/CheckboxList';
import { CodeBlock } from '@astryxdesign/core/CodeBlock';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Heading } from '@astryxdesign/core/Heading';
import { HStack } from '@astryxdesign/core/HStack';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { Spinner } from '@astryxdesign/core/Spinner';
import { Tab, TabList } from '@astryxdesign/core/TabList';
import { Text } from '@astryxdesign/core/Text';
import { VStack } from '@astryxdesign/core/VStack';
import { Download, ExternalLink, GitBranch, MessageSquare, RefreshCw, Scale } from 'lucide-react';
import type {
  GitCommand,
  GoodFirstIssue,
  LicenseInfo,
  PrPhase,
} from '../api/bridge';

const ISSUE_LANGUAGES = ['All', 'Python', 'TypeScript', 'JavaScript', 'Rust', 'Go', 'Documentation'];
const STORAGE_PR_KEY = 'osrg.pr_checklist.v1';

export interface LaunchpadViewProps {
  issues: GoodFirstIssue[];
  issueLanguage: string;
  loadingIssues: boolean;
  licenses: Record<string, LicenseInfo>;
  workflow: PrPhase[];
  gitEssentials: GitCommand[];
  conventionalCommits: { type: string; description: string }[];
  cloningMap: Record<string, boolean>;
  onSelectIssueLanguage: (lang: string) => void;
  onRefreshIssues: () => void;
  onOpenExternal: (url: string) => void;
  onCloneByFullName: (fullName: string) => void;
}

export function LaunchpadView({
  issues,
  issueLanguage,
  loadingIssues,
  licenses,
  workflow,
  gitEssentials,
  conventionalCommits,
  cloningMap,
  onSelectIssueLanguage,
  onRefreshIssues,
  onOpenExternal,
  onCloneByFullName,
}: LaunchpadViewProps) {
  const [subtab, setSubtab] = useState<'issues' | 'licenses' | 'guide'>('issues');
  const [selectedLicenseKey, setSelectedLicenseKey] = useState<string>('');
  const [checkedSteps, setCheckedSteps] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_PR_KEY);
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    const keys = Object.keys(licenses);
    if (keys.length > 0 && !selectedLicenseKey) {
      setSelectedLicenseKey(keys[0]);
    }
  }, [licenses, selectedLicenseKey]);

  const handleToggleChecklist = (values: string[]) => {
    setCheckedSteps(values);
    try {
      localStorage.setItem(STORAGE_PR_KEY, JSON.stringify(values));
    } catch {
      // Ignore storage quota errors
    }
  };

  const totalSteps = useMemo(
    () => workflow.reduce((acc, phase) => acc + phase.steps.length, 0),
    [workflow]
  );

  const selectedLicense = selectedLicenseKey ? licenses[selectedLicenseKey] : undefined;

  return (
    <div className="osrg-page">
      <VStack gap={4}>
        <VStack gap={1}>
          <Heading level={1}>OSS Contributor Launchpad</Heading>
          <Text color="secondary">
            Real beginner-friendly issues, plain-English license decoding, and an interactive First-PR field guide.
          </Text>
        </VStack>

        <TabList
          value={subtab}
          onChange={(v) => setSubtab(v as 'issues' | 'licenses' | 'guide')}
          hasDivider
          role="tablist"
        >
          <Tab value="issues" label="Good First Issues" />
          <Tab value="licenses" label="License Decoder" />
          <Tab value="guide" label="First PR & Git Guide" />
        </TabList>

        {subtab === 'issues' && (
          <VStack gap={4}>
            <HStack justify="between" align="center" wrap="wrap" gap={2}>
              <div className="osrg-chip-row">
                {ISSUE_LANGUAGES.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    className="osrg-filter-pill"
                    data-active={issueLanguage === lang}
                    onClick={() => onSelectIssueLanguage(lang)}
                  >
                    {lang}
                  </button>
                ))}
              </div>
              <Button
                label="Refresh Issues"
                size="sm"
                variant="secondary"
                isLoading={loadingIssues}
                icon={<RefreshCw size={14} />}
                onClick={onRefreshIssues}
              />
            </HStack>

            {loadingIssues && issues.length === 0 ? (
              <HStack gap={2} align="center" style={{ padding: '40px 8px' }}>
                <Spinner size="md" />
                <Text color="secondary">Querying GitHub for open good-first-issue tasks...</Text>
              </HStack>
            ) : issues.length === 0 ? (
              <EmptyState
                icon={<GitBranch size={36} />}
                title="No issues loaded yet"
                description="Click Refresh Issues or try switching the language filter."
                actions={<Button label="Load Issues" variant="primary" onClick={onRefreshIssues} />}
              />
            ) : (
              <VStack gap={3}>
                {issues.map((issue) => (
                  <Card key={`${issue.repo}#${issue.number}`} padding={4} variant="default">
                    <HStack justify="between" align="center" wrap="wrap" gap={3}>
                      <VStack gap={1.5} style={{ flex: '1 1 420px', minWidth: 0 }}>
                        <HStack gap={2} align="center" wrap="wrap">
                          <Badge variant="green" label={issue.repo} />
                          <Text size="sm" color="secondary">
                            #{issue.number}
                          </Text>
                        </HStack>
                        <Heading level={4}>{issue.title}</Heading>
                        <HStack gap={1.5} wrap="wrap" align="center">
                          {(issue.labels || []).slice(0, 4).map((lbl) => (
                            <Badge key={lbl} variant="info" label={lbl} />
                          ))}
                          <Badge
                            variant="neutral"
                            icon={<MessageSquare size={12} />}
                            label={`${issue.comments} comments`}
                          />
                        </HStack>
                      </VStack>

                      <HStack gap={2}>
                        <Button
                          label="Open Issue"
                          size="sm"
                          variant="secondary"
                          icon={<ExternalLink size={14} />}
                          onClick={() => onOpenExternal(issue.html_url)}
                        />
                        <Button
                          label={cloningMap[issue.repo] ? 'Cloning...' : 'Clone Repo'}
                          size="sm"
                          variant="primary"
                          isLoading={Boolean(cloningMap[issue.repo])}
                          icon={<Download size={14} />}
                          onClick={() => onCloneByFullName(issue.repo)}
                        />
                      </HStack>
                    </HStack>
                  </Card>
                ))}
              </VStack>
            )}
          </VStack>
        )}

        {subtab === 'licenses' && (
          <VStack gap={4}>
            <div className="osrg-chip-row">
              {Object.keys(licenses).map((spdx) => (
                <button
                  key={spdx}
                  type="button"
                  className="osrg-filter-pill"
                  data-active={selectedLicenseKey === spdx}
                  onClick={() => setSelectedLicenseKey(spdx)}
                >
                  {spdx} — {licenses[spdx].category}
                </button>
              ))}
            </div>

            {selectedLicense ? (
              <Card padding={5} variant="default">
                <VStack gap={4}>
                  <HStack justify="between" align="center" wrap="wrap" gap={2}>
                    <HStack gap={2} align="center">
                      <Scale size={20} />
                      <Heading level={2}>{selectedLicense.name}</Heading>
                    </HStack>
                    <Badge variant="green" label={selectedLicense.category} />
                  </HStack>

                  <Text size="lg">{selectedLicense.summary}</Text>

                  <div className="osrg-grid-3">
                    <Card padding={3} variant="green">
                      <VStack gap={1.5}>
                        <Heading level={4}>Permissions (You Can)</Heading>
                        {selectedLicense.can.map((item) => (
                          <Text key={item} size="sm">
                            + {item}
                          </Text>
                        ))}
                      </VStack>
                    </Card>

                    <Card padding={3} variant="default">
                      <VStack gap={1.5}>
                        <Heading level={4}>Conditions (You Must)</Heading>
                        {selectedLicense.must.map((item) => (
                          <Text key={item} size="sm">
                            • {item}
                          </Text>
                        ))}
                      </VStack>
                    </Card>

                    <Card padding={3} variant="muted">
                      <VStack gap={1.5}>
                        <Heading level={4}>Limitations (Cannot)</Heading>
                        {selectedLicense.cannot.map((item) => (
                          <Text key={item} size="sm" color="secondary">
                            − {item}
                          </Text>
                        ))}
                      </VStack>
                    </Card>
                  </div>

                  <Banner
                    status="info"
                    title="Best Suited For"
                    description={selectedLicense.recommended_for}
                  />
                </VStack>
              </Card>
            ) : (
              <Text color="secondary">Loading license knowledge base...</Text>
            )}
          </VStack>
        )}

        {subtab === 'guide' && (
          <VStack gap={4}>
            <Card padding={4} variant="default">
              <VStack gap={2}>
                <HStack justify="between" align="center">
                  <Heading level={4}>First Pull Request Progress</Heading>
                  <Badge variant="green" label={`${checkedSteps.length} / ${totalSteps} completed`} />
                </HStack>
                <ProgressBar
                  label="First PR completion progress"
                  isLabelHidden
                  value={checkedSteps.length}
                  max={Math.max(1, totalSteps)}
                  hasValueLabel
                  variant="success"
                />
              </VStack>
            </Card>

            <CheckboxList
              label="Step-by-step PR workflow checklist"
              description="Check off each milestone as you fork, branch, commit, and open your Pull Request."
              value={checkedSteps}
              onChange={handleToggleChecklist}
              hasDividers
            >
              {workflow.flatMap((phase) =>
                phase.steps.map((step, idx) => {
                  const key = `${phase.phase}::${step.title || idx}`;
                  return (
                    <CheckboxListItem
                      key={key}
                      value={key}
                      label={`${phase.phase}: ${step.title}`}
                      description={step.detail}
                    />
                  );
                })
              )}
            </CheckboxList>

            <Heading level={3}>Essential Git Command Reference</Heading>
            <div className="osrg-grid-2">
              {gitEssentials.map((item) => (
                <Card key={item.command} padding={3} variant="default">
                  <VStack gap={1.5}>
                    <HStack justify="between" align="center">
                      <Badge variant="neutral" label={item.category} />
                      <Text size="sm" color="secondary">
                        {item.description}
                      </Text>
                    </HStack>
                    <CodeBlock
                      code={item.command}
                      language="bash"
                      hasLanguageLabel={false}
                      hasCopyButton
                      width="100%"
                    />
                  </VStack>
                </Card>
              ))}
            </div>

            <Heading level={3}>Conventional Commit Prefixes</Heading>
            <Card padding={4} variant="default">
              <div className="osrg-grid-3">
                {conventionalCommits.map((cc) => (
                  <HStack key={cc.type} gap={2} align="center">
                    <Badge variant="green" label={cc.type} />
                    <Text size="sm" color="secondary">
                      {cc.description}
                    </Text>
                  </HStack>
                ))}
              </div>
            </Card>
          </VStack>
        )}
      </VStack>
    </div>
  );
}
