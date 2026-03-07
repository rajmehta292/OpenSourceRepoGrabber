# OpenSource Repo Grabber - Specification Document

## 1. Project Overview

**Project Name:** OpenSource Repo Grabber (OSRG)
**Type:** Desktop Application (Python with CustomTkinter GUI)
**Core Functionality:** A perpetual web scanner that tracks the top 30 all-time and 30 trending open source projects with MIT, Apache 2.0, and BSD licenses, providing comprehensive project details, version history, readmes, news, and AI-powered code explanations via Ollama.
**Target Users:** Developers, researchers, and open-source enthusiasts who want to monitor and explore top open-source projects.

---

## 2. UI/UX Specification

### 2.1 Window Model

- **Main Window:** Single-window application with tabbed navigation
- **Size:** 1400x900 pixels (minimum), resizable
- **Title:** "OpenSource Repo Grabber"
- **Native window controls:** Standard Windows title bar with minimize, maximize, close buttons

### 2.2 Layout Structure

```
+------------------------------------------------------------------+
|  [App Title]                              [Status] [Settings]    |
+------------------------------------------------------------------+
|  [Dashboard] [All-Time Top] [Trending] [Browser] [AI Explain]    |
+------------------------------------------------------------------+
|                                                                   |
|                    MAIN CONTENT AREA                             |
|                                                                   |
|                                                                   |
+------------------------------------------------------------------+
|  [Scanner Status: Running] [Last Update: HH:MM:SS] [60 Repos]    |
+------------------------------------------------------------------+
```

### 2.3 Visual Design

#### Color Palette
- **Primary Background:** #1a1a2e (Deep Navy)
- **Secondary Background:** #16213e (Dark Blue)
- **Card Background:** #0f3460 (Medium Blue)
- **Accent Color:** #e94560 (Coral Red)
- **Success Color:** #00d9a0 (Mint Green)
- **Warning Color:** #ffc107 (Amber)
- **Text Primary:** #ffffff (White)
- **Text Secondary:** #a0a0a0 (Gray)
- **Border Color:** #2a2a4a (Muted Purple)

#### Typography
- **Font Family:** Segoe UI, system default
- **Heading 1:** 24px, Bold
- **Heading 2:** 18px, SemiBold
- **Body:** 14px, Regular
- **Caption:** 12px, Regular
- **Monospace (Code):** Consolas, 13px

#### Spacing System
- **Base Unit:** 8px
- **Card Padding:** 16px
- **Section Margin:** 24px
- **Element Gap:** 12px

#### Visual Effects
- **Card Shadows:** 0 4px 12px rgba(0,0,0,0.3)
- **Hover Effects:** Brightness increase 10%, border glow
- **Transitions:** 200ms ease-in-out
- **Scrollbars:** Custom styled, thin, accent colored

### 2.4 UI Components

#### Navigation Tabs
- Dashboard, All-Time Top, Trending, Browser, AI Explain
- Active state: Accent color underline, brighter text
- Hover state: Background lighten 5%

#### Project Cards
- Display: Project name, description (truncated), license badge, stars, forks
- States: Default, Hover (elevated shadow), Selected (accent border)
- Click action: Open detail view

#### Status Indicators
- Scanner running: Pulsing green dot
- Scanner paused: Yellow dot
- Error state: Red dot
- Updating repo: Spinning loader

#### Built-in Browser
- URL bar with navigation buttons (back, forward, refresh)
- WebView2-based embedded browser
- Loading indicator

#### AI Explanation Panel
- Code input text area
- "Explain with Ollama" button
- Response display area with markdown support

---

## 3. Functional Specification

### 3.1 Core Features

#### 3.1.1 Repository Discovery & Tracking

**All-Time Top Repositories:**
- Fetch top 30 repos by stars across all time
- Filters: MIT, Apache 2.0, BSD-3-Clause, BSD-2-Clause licenses
- Sort by: Stars (default), Forks, Recent activity

**Trending Repositories:**
- Fetch 30 trending repos (based on stars gained this week)
- Same license filters as above
- Updated every scan cycle

**Scan Frequency:**
- Default: Every 30 minutes
- Configurable: 15min, 30min, 1hr, 2hr
- Manual refresh button available

#### 3.1.2 Repository Data Collection

For each tracked repository, collect:
- Basic info: Name, full name, description, URL
- License: Type, full text link
- Stats: Stars, forks, watchers, open issues
- Metadata: Primary language, topics, created_at, updated_at, pushed_at
- Readme: Full markdown content
- Version tags: List of release tags with dates
- Contributors: Top 10 contributors
- Recent commits: Last 10 commits
- News/Activity: Recent releases, issues, PRs

#### 3.1.3 GUI Features

**Dashboard Tab:**
- Total repositories tracked: 60
- Scanner status indicator
- Last update timestamp
- Quick stats: Total stars across all repos
- Recent activity feed (last 10 events)
- Top 5 most starred repos

**All-Time Top Tab:**
- Grid/List view toggle
- Sortable columns: Name, Stars, Forks, License, Language, Updated
- Search/filter bar
- Pagination (10 per page)
- Click to view details

**Trending Tab:**
- Same layout as All-Time Top
- Shows trending score (stars gained this week)

**Browser Tab:**
- Embedded WebView2 browser
- URL bar with Go button
- Navigation: Back, Forward, Refresh, Home (to GitHub)
- Bookmarks for quick access to tracked repos
- Current page title display

**AI Explain Tab:**
- Text area for pasting code or URL to repo
- "Explain Code" button
- "Summarize Project" button
- "Get Latest News" button
- Response display with markdown rendering
- Copy response button
- Clear button

#### 3.1.4 Ollama Integration

**Available Models:** llama3.2, qwen2.5, mistral (free cloud models)

**Features:**
- Explain code: Take code snippet, return detailed explanation
- Summarize project: Give overview of repo based on readme
- Answer questions: Ask about tracked projects

**Implementation:**
- Local Ollama server connection (localhost:11434)
- Fallback: Display message if Ollama not available
- Model selector dropdown
- Temperature/max tokens configuration

### 3.2 User Interactions

1. **Launch App:** App starts, loads cached data, begins background scanning
2. **View Repos:** Navigate tabs, click cards, view details
3. **Browse Web:** Use built-in browser to visit repo pages
4. **Get AI Help:** Paste code, click explain, read response
5. **Manual Refresh:** Click refresh to immediately update all repos
6. **Configure Settings:** Click settings, adjust scan interval, choose Ollama model

### 3.3 Data Flow & Architecture

```
+------------------+     +-------------------+     +------------------+
|   GitHub API     |---->|   Scanner Service |---->|   SQLite DB      |
|   (Data Source)  |     |   (Background)    |     |   (Storage)      |
+------------------+     +-------------------+     +------------------+
                                  |
                                  v
                         +-------------------+
                         |   Event System    |
                         +-------------------+
                                  |
                                  v
                         +-------------------+
                         |   GUI Layer       |
                         |   (CustomTkinter) |
                         +-------------------+
                                  |
                                  v
                         +-------------------+
                         |   Ollama API      |
                         |   (AI解释)        |
                         +-------------------+
```

**Key Modules:**

1. **github_api.py:** GitHub API client, rate limit handling, data fetching
2. **scanner_service.py:** Background thread, scheduling, repository updates
3. **database.py:** SQLite operations, schema, CRUD functions
4. **models.py:** Pydantic data models
5. **gui.py:** Main GUI application, all tabs and components
6. **ollama_client.py:** Ollama API integration
7. **browser.py:** WebView2 browser component
8. **utils.py:** Helper functions

### 3.4 Edge Cases

- **GitHub Rate Limit:** Display warning, use cached data, retry after reset
- **Network Offline:** Use cached data, show offline indicator
- **Ollama Unavailable:** Show setup instructions, disable AI features gracefully
- **Repository Deleted:** Mark as unavailable, gray out in UI
- **Large Readme:** Truncate in list view, full in detail view
- **Scan Failure:** Log error, continue with valid repos, show error indicator

---

## 4. Acceptance Criteria

### 4.1 Functional Criteria

- [ ] App launches without errors and displays main window
- [ ] Dashboard shows correct counts and stats
- [ ] Top 30 all-time repos are fetched and displayed correctly
- [ ] Trending 30 repos are fetched and displayed correctly
- [ ] License filtering works (only MIT, Apache 2.0, BSD shown)
- [ ] Scanner runs in background and updates every 30 minutes (configurable)
- [ ] Project cards show name, description, stars, forks, license
- [ ] Clicking a card opens detail view with full information
- [ ] Readme displays properly with markdown rendering
- [ ] Version history shows release tags with dates
- [ ] Built-in browser loads pages and navigates correctly
- [ ] Ollama integration explains code when provided
- [ ] Settings allow changing scan interval and Ollama model
- [ ] App handles GitHub API rate limits gracefully
- [ ] Offline mode uses cached data

### 4.2 Visual Criteria

- [ ] Dark theme with specified color palette applied
- [ ] Cards have proper shadows and hover effects
- [ ] Navigation tabs highlight correctly on selection
- [ ] Status indicators show correct colors
- [ ] Typography matches specification
- [ ] Layout is responsive and resizable
- [ ] Loading states show appropriate indicators

### 4.3 Performance Criteria

- [ ] App starts in under 5 seconds
- [ ] Tab switches are instant (<100ms)
- [ ] Repo list loads in under 2 seconds
- [ ] Background scanning doesn't freeze UI
- [ ] Memory usage stays under 500MB during normal operation
