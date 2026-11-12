"""
Open Source Contributor & Learner Guide Knowledge Base
Provides interactive checklists, Git cheatsheets, and license guides for learners.
"""

FIRST_PR_WORKFLOW = [
    {
        "phase": "1. Discovery & Alignment",
        "steps": [
            "Search repositories with the 'good-first-issue' or 'help-wanted' labels.",
            "Carefully read the repository's README.md, CONTRIBUTING.md, and Code of Conduct.",
            "Comment on the open issue to express interest: 'Hi! I would love to work on this issue if it is still available.'",
            "Wait for a maintainer to assign or confirm before writing extensive code."
        ]
    },
    {
        "phase": "2. Environment & Forking",
        "steps": [
            "Fork the repository to your own GitHub account via the 'Fork' button.",
            "Clone your fork locally: git clone https://github.com/your-username/repo-name.git",
            "Add the original repository as an upstream remote: git remote add upstream https://github.com/original-owner/repo-name.git",
            "Install project dependencies into an isolated virtual environment or container."
        ]
    },
    {
        "phase": "3. Branching & Clean Coding",
        "steps": [
            "Always create a fresh topic branch: git checkout -b fix/short-description",
            "Keep changes minimal, laser-focused on the issue at hand (avoid unrelated formatting edits).",
            "Follow the project's existing code style, naming conventions, and docstring formatting.",
            "Run existing test suites and linters locally before staging changes."
        ]
    },
    {
        "phase": "4. Committing & Pushing",
        "steps": [
            "Use clear, conventional commit messages: 'fix: resolve typo in authentication headers'.",
            "Stage only modified files: git add <files>",
            "Commit your changes: git commit -m 'type: concise description'",
            "Push your branch to your personal fork: git push -u origin fix/short-description"
        ]
    },
    {
        "phase": "5. Submitting & Collaborating",
        "steps": [
            "Open GitHub and click 'Compare & pull request'.",
            "Fill out the repository's PR template thoroughly.",
            "Reference the issue number in the PR description: 'Fixes #42' or 'Closes #108'.",
            "Be patient and polite during review. Address reviewer feedback promptly by pushing new commits to the same branch."
        ]
    }
]

GIT_ESSENTIALS = [
    {
        "category": "Setup & Remote",
        "command": "git remote -v",
        "description": "List all configured remote repositories (origin and upstream)."
    },
    {
        "category": "Setup & Remote",
        "command": "git remote add upstream <url>",
        "description": "Connect your local clone to the original repository to fetch updates."
    },
    {
        "category": "Branching",
        "command": "git checkout -b <branch-name>",
        "description": "Create a new branch and switch to it immediately."
    },
    {
        "category": "Branching",
        "command": "git branch -a",
        "description": "List all local and remote tracking branches."
    },
    {
        "category": "Synchronizing",
        "command": "git fetch upstream && git merge upstream/main",
        "description": "Bring changes from the original repository into your local branch."
    },
    {
        "category": "Staging & Commits",
        "command": "git status -s",
        "description": "View short-format status of modified, untracked, and staged files."
    },
    {
        "category": "Staging & Commits",
        "command": "git commit -m \"feat: description\"",
        "description": "Commit staged changes with a descriptive conventional message."
    },
    {
        "category": "Pushing",
        "command": "git push -u origin <branch-name>",
        "description": "Push branch to your fork and set upstream tracking."
    }
]

CONVENTIONAL_COMMITS = [
    ("feat", "A new feature or enhancement for the user or consumer."),
    ("fix", "A bug fix in the application or library."),
    ("docs", "Documentation-only changes (README, docstrings, guides)."),
    ("test", "Adding missing tests or correcting existing tests."),
    ("refactor", "Code change that neither fixes a bug nor adds a feature."),
    ("chore", "Routine maintenance, dependency updates, or build tooling.")
]

