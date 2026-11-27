# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.7.2] - 2026-11-27

### Changed

- **Review page**: the name prompt no longer has a note under it about
  who sees the name and when it was watched.

## [2.7.1] - 2026-11-26

### Fixed

- **Review page comments** no longer scroll sideways and cut off their
  left edge while one is highlighted at the playhead.

## [2.7.0] - 2026-11-26

### Changed

- **Video Start** replaces Pre-Roll in a review link's settings: type
  the timecode of the video's first frame instead of how much plays
  before the IN. Left empty, the video starts at the version's IN.
  Existing pre-rolls become the current version's IN less the pre-roll,
  so its comments keep their timecodes.

### Fixed

- **A cue's page** no longer fails to open when its review link has a
  pre-roll of an hour or more.

## [2.6.1] - 2026-11-24

### Fixed

- **"Part of this page didn't load"** no longer appears when a script
  added by a browser extension or a proxy is blocked. When one of
  ReelTime's own scripts fails, the page tries twice before saying so,
  pausing before the second try, and the browser's console names the
  script.
- **Project titles** on Projects and the Overview stay readable in a
  narrow window instead of shrinking to a letter, and the
  top bar no longer runs past the edge of one.

## [2.6.0] - 2026-11-18

### Changed

- **One place for each command on the cue overview.** Import and Export
  are in the toolbar, Stats is beside the views, and the Tools menu holds
  only what works on cues. The More menu keeps Export Cue Sheet and Copy
  JSON there, and still has Import, Export and Stats on the other project
  pages. The **Project** settings page is now **Duplicate, Archive or
  Delete**, so it can't be mistaken for General.
- **Conform** names the cues each reel's shift moves, shows unchanged
  offsets as a dash, and marks the ones that moved in amber.
- **The timeline** is one Tab stop: the arrow keys, Home and End move
  between cues, and Alt+↑/↓ moves a cue to another lane.
- **Fields and switches** have a stronger edge, so they're easy to find
  in both themes. In the light theme, green and grey text is a little
  darker, for contrast on project-tinted pages.
- **On a phone**, the grid's Filter and View menus rise from the bottom
  instead of running off the screen, and a review link's range handles
  are easier to grab.
- **Project pages load faster**: the notes editor loads the first time a
  note opens.
- **One green button per page** on the cue page (Save Shares is quiet)
  and the Picture page (Place Cues is quiet).
- **Headings in order on project pages.** A page's own title (Conform,
  Activity, a settings page) is its main heading, and its sections come
  next; the project's name above it is no longer a heading there. The
  cue overview, which has no title of its own, keeps the project's name
  as its heading.
- **New typeface: IBM Plex Sans** replaces Instrument Sans in the app
  and in PDFs. It's the sister of IBM Plex Mono, which already sets the
  timecodes, so words and numbers come from one family made for
  interfaces and data.
- Removed the Alpine.js file that was shipped but never used.
- **Calmer edges.** The cue page's current version card and the project
  cards on Overview and Projects show their colour around the whole
  edge instead of a thick bar on one side. So do messages, form
  errors, the Schedule's list of deadlines at risk, the Conform summary
  and a note's "saved elsewhere" box.

### Fixed

- **The cue page beside a DAW:** at half-screen widths, its section list
  no longer slides over the fields; it becomes one row of links.
- **A dialog's address opened directly** (Import, Export, Export Cue
  Sheet, a cue's History, conform strip or Review section) opens its page
  with the dialog or section showing, not a bare unstyled fragment.
- **A review link's "Last opened"** no longer counts the editor or admin
  who sent it checking how it looks.
- **Status colours** pick dark or light text by contrast, so every label
  stays readable.
- **A timeline drag that's interrupted** puts the cue back and saves
  nothing.
- The Projects page's hidden Search button no longer takes keyboard
  focus.

## [2.5.0] - 2026-11-17

### Added

- **Notifications** (profile menu): ReelTime tells your phone or browser
  when someone comments on or replies to a review link, or opens one.
  The project's name is the title, and tapping it opens the cue's page
  at that version. On an iPhone or iPad, add ReelTime to the Home Screen
  first (iOS 16.4 or later); it then opens as an app of its own. Choose
  what you're told about, send a test, and remove devices on the same
  page. A guest's name always says "(guest)", and several comments on
  one cue close together arrive as one. See Help, Notifications.
- ReelTime has a web app manifest and icons, so a Home Screen or
  desktop install opens it full screen.

### Changed

- **Comments on a review page's timeline** are speech bubbles pointing
  at their frame, not small dots, so they're easy to see and to click.

### Fixed

- A version whose picture has a long name no longer pushes the cue
  page's **Versions** list sideways, cutting off its title and labels:
  the name ends in "…", with the whole name on hover.

### Deployment

- Notifications are sent by the scheduler service, which now also runs
  every few seconds. Without Docker, enable the new
  `reeltime-push.service` (`systemctl enable --now reeltime-push.service`
  after re-running `deploy/systemd/install.sh`). It needs to reach
  Apple's, Google's, Mozilla's and Microsoft's push services.
- The key that signs notifications is made on first use and kept in the
  data directory as `vapid.pem`; `REELTIME_VAPID_PRIVATE_KEY` sets one
  instead. Push subscriptions aren't in backups: after a restore, turn
  notifications on again on each device.
- The Content Security Policy adds `worker-src 'self'` and
  `manifest-src 'self'`.

## [2.4.0] - 2026-11-17

### Added

- **Name on Review Pages** (Settings → Look): review links show
  this name, such as the composer's, at the top and in the browser tab
  instead of ReelTime.

## [2.3.0] - 2026-11-17

### Changed

- **Dialog buttons** are right-aligned, Cancel then the action, in every
  dialog, and wrap on a phone instead of breaking their labels over
  several lines. The buttons of a question (Delete, Reset Schedule) no
  longer sit in a strip set in from the dialog's edges.
- **Questions before something that can't be undone** always have a
  red button: Revoke Link and Make a New Link were green. The buttons
  that ask (Revoke Link on a cue, Delete in Settings → Views) are plain,
  like the other buttons beside them.
- **Section titles** inside a page are one size everywhere: they were
  nearly as big as the page title on Conform, Backup and the Overview,
  and the size of body text in Settings.
- **Pick-one choices** (Row Size in the View menu, Export, Format,
  the tools) look the same everywhere: the one picked is tinted green
  with its text in the normal colour. On a phone a group that wraps
  stands apart instead of breaking its joined corners.
- **Log a Turnover** and **Edit Turnover** keep the project bar, with
  the title and **?** link of the other project pages. Their notes on
  what unticking a reel does are in Help.
- **Messages** have one shape: a bar on the left tinted by kind, the
  text in the normal colour. Saved, error and Import's problems and
  warnings looked different; the cue page's "Not saved." is now red and
  names the field.
- **Menus:** the right-click menu is the same size as the Tools and
  More menus beside it; every command that opens a dialog ends in
  "…"; menus, popovers, the date picker and tips share one surface.
- **Empty lists** say what's missing ("No themes yet.", "No writers
  yet.") in one quiet line, instead of "None yet." in five styles. The
  empty grid uses the same empty-state box as the other pages.
- **Save buttons:** Credits' Save Changes is first on the left like
  every other form's, and the cue page's Save Shares is a primary
  button. Page actions (Export on Credits, Activity and Trash) are full
  size.
- **Icon buttons** (×, drag handles, the calendar button, the notes
  tools) are one size and shape, where there were seven sizes and three
  shapes.
- **Status colours** are the same small square in the status editor
  as in the filters and the Schedule (it was a circle there), and the
  three kinds of count (Credits, notes cells, the filter button) share
  one pill.
- **Fields:** a field's error sits right under its box, above any
  hint; the view editor's boxes match every other dialog's; the review
  link's name hint is a hint, not body text.
- **Focus** is the same ring everywhere: the avatar and colour swatches
  used a darker green, the notes editor and Credits' cells showed a
  green border instead, and a few buttons drew the ring flush against
  their edge.
- **Dialog widths:** Export Cues and Export Cue Sheet are the medium
  width, like the other short dialogs, instead of the widest.
- **Difficulty bars** use the app's own amber and red, so they follow
  the light theme like everything else.
- **Small text** is one size: the 11–13.6px labels (keyboard keys,
  stats, tips, the toolbar, notes) are all 13px.

## [2.2.0] - 2026-11-17

### Added

- **Review comments on a stretch of the video.** On a review page the
  comment being written has a handle each side of the frame on screen;
  dragging one stretches the comment over part of the video. Such a
  comment lists both timecodes, and its part of the timeline is
  coloured while the video is inside it.
  `review_comments` (MCP) gives where it ends as `to`.

## [2.1.0] - 2026-11-13

### Added

- **Review links.** A cue's page has a **Review** section that makes a
  link for someone without an account: they watch the cue's bounce
  against its timecode and comment on the frame on screen or on the
  whole cue.
  - The video is each version's **File Link**, now at the top of
    Review, when that is a Dropbox link to a single file; ReelTime
    doesn't hold video. The same link follows new versions, and comments
    stay with the version they were made on.
  - A version can also have an **Audio Link**, the music alone, which
    plays in its own small player under the video.
  - A link can have a password and a last day, can be closed to
    comments and can be revoked. Its settings are in the section and
    save as they change.
  - Reviewers reply to each other's comments. Signed in, an editor also
    resolves and deletes comments on the review page.
  - A guest gives their name before the video shows, and the cue's
    page lists who watched each version: when, how long the video or
    audio played, how far they got and how long the page was open. Only
    the name is kept about a guest.
  - The grid has an **Open Notes** column: the comments on each cue's
    current version not yet resolved.
  - Every comment, reply, resolve and deletion is in Activity, where it
    undoes. See Help, Review Links.
- `REELTIME_TRUSTED_PROXIES` (optional) lists the proxies' addresses.
  Only they are then believed about a visitor's address and HTTPS, so
  something else that can reach ReelTime's port can't forge either.
- AI assistants (MCP): `review_comments` reads a cue's review comments,
  `reply_to_comment` answers one and `resolve_comment` marks it dealt
  with.
- The grid's right-click menu on a cue starts with **Details**, which
  opens the cue's page.

### Fixed

- Rate limits counted per hour forgot their count after five idle
  minutes, so the emergency admin login's five tries an hour and the
  backup limit could be exceeded by pausing between bursts. Counters
  now last their whole window, and the cache that holds them is no
  longer small enough to be flushed by a flood of requests.
- Credits, Recent Changes: entries were drawn in a dark box with a
  rule through them and cut-off labels; they shared class names with
  the grid's timeline. They wrap and line up again.
- Undo no longer takes away a version, a cue or a review comment that
  reviewers have commented on or replied to since; it says to delete it
  from its page instead, which undoes with the comments.

### Security

- The review page, and only it, may load video from `www.dropbox.com`
  and `*.dropboxusercontent.com` (`media-src`). It and what it posts to
  are reachable without signing in, by the link's secret address:
  rate-limited per client address, password tries per link as well, and
  never cached or indexed.

## [2.0.1] - 2026-11-13

### Fixed

- Log Written: the list of logs no longer slides under the Log and
  Cancel buttons; it sits above them.
- A dialog that opens on a date field keeps the focus on it; adding the
  calendar button had dropped the focus to the page.

## [2.0.0] - 2026-11-12

### Changed

- **ReelLife is now ReelTime**, everywhere: the app, the image
  (`ghcr.io/nhadler/reeltime`), the repository (`nhadler/ReelTime`;
  GitHub forwards the old address), the `reeltime` command and Python
  package, `REELTIME_*` settings, paths, service names, the default
  PocketID groups and the AI assistant's `reeltime://` resources. The
  old names don't work any more. To upgrade an install:
  1. Stop it.
  2. Rename every `REELLIFE_*` setting in `.env` (or
     `/etc/reellife/reellife.env`) to `REELTIME_*`, and point
     `REELTIME_IMAGE` at `ghcr.io/nhadler/reeltime`.
  3. In the data directory, rename `reellife.sqlite3` (and any
     `-wal` and `-shm` files beside it) to `reeltime.sqlite3`. ReelTime
     won't start while only the old file is there.
  4. Docker Compose: the project is `reeltime` and its volume
     `reeltime-data`; copy the old volume across, e.g.
     `docker run --rm -v reellife_reellife-data:/from -v reeltime_reeltime-data:/to alpine cp -a /from/. /to/`
     (or keep your own bind mount). systemd: the units are
     `reeltime.service` and `reeltime-snapshot.timer`, the checkout
     `/opt/reeltime`, settings `/etc/reeltime/reeltime.env` and data
     `/var/lib/reeltime`; move those across and run `install.sh` again.
  5. PocketID: rename the groups to `reeltime-admins`, `reeltime-editors`
     and `reeltime-viewers`, or set `OIDC_GROUP_*` to the old names.
  6. Start it. The grid's remembered views, filters and row size reset
     once in each browser. Backups made before the rename still
     restore.

### Fixed

- Quieter logs: a request for a host the server doesn't serve is logged
  as a one-line warning instead of an error with a traceback, and
  Fontconfig no longer warns at startup that it has no cache directory
  (the image and systemd unit give it one).

## [1.6.0] - 2026-11-12

### Changed

- **Log Written** takes the stretch you wrote as timecodes, From and To,
  instead of an amount. From starts where your last log ended (else the
  cue's IN), To at its OUT. A cue can have several logs a day; overlaps
  count once in the schedule and % Written. The dialog lists the cue's
  logs, each with Remove. Older logs keep counting as amounts. The AI
  assistant's `log_written` takes `tc_from` and `tc_to` too, and an
  amount now adds a log rather than replacing the day's.

## [1.5.2] - 2026-11-12

### Fixed

- A request for a host ReelLife doesn't serve (not in
  `REELLIFE_ALLOWED_HOSTS`, such as the server's bare IP) gets a 400
  again, not a 500: its error page no longer expects a signed-in user.

## [1.5.1] - 2026-11-12

### Fixed

- A long note in the notes panel stays inside its box (the text ran on
  below the box's border), and the toolbar stays at the top while the
  note scrolls.
- **No Pin** on a column the grid pins by default (Status, % Written,
  Cue #, Title, Thumbnail, #) now sticks after a reload.

## [1.5.0] - 2026-11-12

### Added

- **% Written** column, after Status in the Standard view: how much of
  each cue is written, from Log Written, as a bar in the status colour.
  Marking a cue composed (or approved) makes it 100%; until then logged
  work stops at 99%. Revisions count their own work from 0%, striped.
  Clicking the percent opens Log Written, and the bar follows at once.
  It sorts, exports, and is added after Status to projects' own
  Standard views.
- `deploy/google-calendar`: a Google Apps Script, run in your own
  Google account, that copies the Calendar Feed into a Google calendar
  every 10 minutes. Google Calendar itself fetches a subscribed feed
  only every few hours.

## [1.4.0] - 2026-11-12

### Changed

- Notes are written as formatted text in the notes panel: no more
  separate Write and Preview. Bold, headings, lists, check lists,
  quotes and links show as you type, check boxes tick in place, and
  notes are still kept as Markdown. The editor is TipTap, bundled into
  the app; HTML in a note stays text, and links go only to web and mail
  addresses.

### Fixed

- Check boxes pasted from elsewhere (☐, ☑) count and tick as a check
  list.
- The grid shows `---` as a rule and a backslash-escaped character
  (`\*`) as the character.

## [1.3.1] - 2026-11-12

### Fixed

- The cue grid could stay empty with no message when the browser failed
  to fetch one of its scripts (seen in Firefox over HTTP/3): one
  missing module stops every module that imports it. Scripts now import
  each other by their cached-for-good names, so a page load fetches far
  fewer files, and if a script still fails to load, or gets no answer
  for 15 seconds, the page reloads once, then says "Part of this page
  didn't load. Reload the page."
- A page left open after its session ended (8 hours idle, or 7 days)
  now says "You've been signed out. Reload the page to sign in again."
  The grid used to stay empty and an edit could be lost without a
  word; the grid's requests now get a clear answer instead of the
  sign-in page, and a dialog reloads the page to sign in.

## [1.3.0] - 2026-11-12

### Added

- **Reset Schedule** unpins every cue in a project in one undoable
  change, from the project's More menu or the Schedule when only that
  project is shown. Logged written work stays.

### Changed

- Buttons shrink slightly while pressed (not with reduced motion), and
  the loading indicator fades in faster.

### Fixed

- The cue grid no longer stays empty when its cues are slow to arrive. A
  load that stalls for 20 seconds, can't connect or gets a server error
  (a proxy's 502 or 524) is tried again, up to three times. The grid's
  data is also compressed, so it crosses a slow upload faster.

## [1.2.0] - 2026-11-09

### Added

- **Color** (Project Settings, General, or New Project): one of eight
  colours, or Automatic. It tints the project's pages (a stripe on the
  project bar, the bar and page washed lightly toward it; actions stay
  green), marks its card on Projects and the Overview, and colours its
  cues on the Schedule. Choosing one previews it before saving.

### Fixed

- AI assistants can sign in when PocketID is behind Cloudflare. ReelLife
  now names itself when it fetches PocketID's signing keys, so
  Cloudflare's Browser Integrity Check no longer refuses the request.

## [1.1.0] - 2026-11-09

### Added

- The profile menu shows ReelLife's version. When a newer release is
  out, admins see it there in amber with a link to its notes, and a dot
  on their picture. The scheduler checks GitHub once a day;
  `REELLIFE_UPDATE_CHECK=false` turns the check off.

### Changed

- Notes are written in a panel beside the grid: click a notes cell or
  press Enter on it. It has a Markdown toolbar (bold, italic, heading,
  lists, check lists, links) with shortcuts, a Preview whose check boxes
  can be ticked, saving as you type, and Alt+↑/↓ to move to the cue
  before or after. Grid cells show notes formatted, with check-list
  progress ("3/7"), and hovering shows the whole note in a card you can
  scroll.
- The calendar feed has an event for each cue on each day it's planned,
  titled with the cue and that day's music ("1m02 Main Title (0:43 of
  2:32)"), instead of one event a day listing them.
- Runs on Django 6.1.3 and AG Grid 36.3.0.

### Fixed

- A very long cue number or Shift offset can no longer keep the server
  busy matching it.

## [1.0.0] - 2026-11-01

The first stable release.

### Added

- **Schedule On…** (the cue page's ⋯ menu, the grid's right-click menu,
  or a day's list on the Schedule): pin a cue to a day and the rest of
  the plan flows around it; a pin marks it on the calendar. Undoable.
- **Calendar Feed** (profile menu): a private link your calendar app
  subscribes to, one event a day listing its cues, the last 30 days and
  the next 90; revoke or replace it any time, or download an .ics once.
- **Log Written…** (a day's list on the Schedule, the grid's toolbar
  with one cue ticked, the cue page's ⋯ menu, the grid's right-click
  menu): how much of a cue you wrote on a
  day. The schedule counts only logged work as done and plans the rest;
  past days show what was planned beside what was written. Undoable.
- The Schedule keeps each day's plan, so past days show what was
  planned, faded. The summary starts "On track" when every deadline is
  met.
- MCP tools `schedule` ("what should I write today?"), `pin_cue` and
  `log_written`.
- **Projects at Once** (Settings, Schedule): work every project each
  day, each at its own pace to its own deadlines (In parallel, the
  default), or one at a time, earliest deadline first. With a daily
  maximum, projects asking for less than an even share keep all of it.

### Changed

- The Schedule's month fills the window instead of scrolling: weeks
  share the height, each day shows the cues that fit (titles on one
  line) and says how many more. Choosing a day swaps its list in
  without reloading the page.
- Runs on Django 6.1.
- Empty pages (Projects, Overview, Picture, Activity, Trash) show an
  icon, a short title and, where there's something to do, the button
  for it.
- Dialogs come in two widths; the Cue Sheet dialog's button says Export
  Cue Sheet, and Edit View has a × like the others.
- Import and Restore Backup drop zones show a file, not a picture.
- Days off on Your Days Off are hatched, as on the Schedule.
- A page that doesn't exist shows Page Not Found inside the app, with a
  way back to the Overview.
- Cues without a thumbnail show the project's initials in the grid.
- App Settings is one sheet: each section a row, its controls lined up
  on shared columns, so the page fits a laptop screen without
  scrolling. Viewers see it read-only.
- A project's work waits for its composition deadline's start date: the
  Schedule plans nothing for it before then, and Per Day counts the
  days from the start. Other projects have those days to themselves.
- New Project and every Project Settings page use the App Settings
  layout: each section's name in a left column, its fields beside it,
  and a rule between sections.
- Empty choices in every menu show a dash.
- Option labels are in Title Case throughout, and blank choices show a
  dash. Two to four choices are one segmented control; longer lists are
  menus. Explanations moved from dialogs into Help.
- Tall grid rows start every cell on the first line, and wrapped text
  stops at six lines with a fade.
- The project bar's menu is called More; the selection bar's actions
  are buttons; empty lists show one line and Add.
- On a phone the top bar's links fade at the edge, and the cue page
  skips its section index.
- Clarified Help text, UI descriptions, and contributor documentation.
- The grid's toolbar has Export beside Import.
- Picture names use an en dash everywhere ("Reel 1 – c0917").
- Timecodes and cue numbers are set in mono in tool previews, the
  viewer's cue page, Shift's fields and the cue page's ‹ › buttons.
- The Schedule On dialog's title reads "Schedule On: 1m01".
- New Project's deadline names match the other field labels.
- Calendar Feed's Make a Link and Download .ics sit side by side.
- In the light theme, pale statuses (To Write) have a thin outline.

### Fixed

- A project card's ⋯ menu was cut off at the card's edge.
- A project card's deadline label ("Composition Nov 22") was cut off.
- A fresh install no longer takes a needless snapshot before its first
  migration.
- Menus and the Filter panel no longer run past the bottom of the
  window.
- Delete Project stays disabled until the project's title is typed.
- On a phone, project cards no longer cut off their figures' captions
  or start a line with a stray "·".
- Opening Breakdown no longer moves the project bar's links.

## [0.4.0] - 2026-11-01

The first public release.

### Added

- **Projects** for films and episodes, with picture types (reels, acts,
  clips or long play), any frame rate including drop-frame, deadlines,
  days off, thumbnails and series.
- **Turnovers and picture versions**, with a conform page that shows
  which cues were written to older picture and shifts them by reel.
- **The cue grid:** reels on a timeline, coloured statuses, inline
  editing, filters, saved views (Standard, Spotting, Conform,
  Orchestration, Recording, Mixing, Viewer, Cue Sheet), a stats panel,
  bulk edits, cue tools (New Cues, Split, Merge, Renumber, Shift, Move,
  Copy, Delete) and undo for every change.
- **Cue details:** versions with their own notes, themes, sub status and
  the picture they were written to; department statuses; history with
  revert.
- **Imports** from Pro Tools Session Info as Text (clips or markers),
  Cubase and Nuendo, MIDI markers, and Excel or CSV, with a preview.
  Cue numbers must fit the project's Valid Cue Numbers.
- **Exports:** cue logs (Excel, CSV), PDF reports and wall charts,
  version notes, and RapidCue cue sheets with writers, publishers and
  shares.
- **Overview and Schedule:** this week across projects, and a daily
  writing plan weighted by difficulty and spread to each deadline.
- **Credits:** writers and publishers with default shares per project
  and series.
- **Activity and Trash** per project: undo any change, restore deleted
  cues.
- **Search** (Ctrl+K) across projects, cues and notes, and keyboard
  shortcuts throughout.
- **Help** pages, with the version and a link to the source.
- **MCP server** at `/mcp` so AI assistants can read and edit with the
  same roles as people.
- **Sign-in** through OIDC with PKCE (PocketID by default), roles from
  the provider's groups, and an emergency local admin.
- **Backup and restore** in one file, plus nightly database snapshots.
- **Deployment:** a hardened multi-architecture image at
  `ghcr.io/nhadler/reellife` with an SBOM and build provenance, Docker
  Compose, and a systemd + uv install.

[Unreleased]: https://github.com/nhadler/reeltime/compare/v2.7.2...HEAD
[2.7.2]: https://github.com/nhadler/reeltime/compare/v2.7.1...v2.7.2
[2.7.1]: https://github.com/nhadler/reeltime/compare/v2.7.0...v2.7.1
[2.7.0]: https://github.com/nhadler/reeltime/compare/v2.6.1...v2.7.0
[2.6.1]: https://github.com/nhadler/reeltime/compare/v2.6.0...v2.6.1
[2.6.0]: https://github.com/nhadler/reeltime/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/nhadler/reeltime/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/nhadler/reeltime/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/nhadler/reeltime/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/nhadler/reeltime/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/nhadler/reeltime/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/nhadler/reeltime/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/nhadler/reeltime/compare/v1.6.0...v2.0.0
[1.6.0]: https://github.com/nhadler/reellife/compare/v1.5.2...v1.6.0
[1.5.2]: https://github.com/nhadler/reellife/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/nhadler/reellife/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/nhadler/reellife/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/nhadler/reellife/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/nhadler/reellife/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/nhadler/reellife/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/nhadler/reellife/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/nhadler/reellife/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/nhadler/reellife/releases/tag/v1.0.0
[0.4.0]: https://github.com/nhadler/reellife/commit/1d2429b
