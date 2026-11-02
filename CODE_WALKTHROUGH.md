# Live AI Copilot: code walkthrough

This guide follows the application from browser startup through a local AI
response. It explains the frontend, Chrome extension pieces, backend, tests,
and local infrastructure in source order. Consecutive CSS declarations and
small configuration fields are explained together where they have one purpose.

## 1. What runs, and how the pieces connect

The project currently has two related browser-facing pieces:

1. **Popup UI** — the React application opened by clicking the extension icon.
   It restores the saved enabled flag, checks the active tab, injects the page
   overlay, and lets the user disable it.
2. **Page overlay** — plain JavaScript injected into the current webpage. It
   reads page text, notices DOM changes, and requests suggestions.

The request path is:

```text
Chrome popup (React)
    └─ injects frontend/public/overlay.js into an HTTP(S) tab
          └─ chrome.runtime.sendMessage({ type: "COPILOT_CHAT", payload })
                └─ frontend/public/service-worker.js
                      └─ POST http://127.0.0.1:8000/api/chat
                            └─ backend/app/main.py
                                  └─ backend/app/services/ai_provider.py
                                        └─ local Ollama model
```

The extension popup and the injected overlay are different JavaScript
execution contexts. The overlay uses Chrome's extension messaging API rather
than calling the backend directly. The service worker is the bridge that has
the backend host permission.

The Python backend has two AI endpoints: `/api/chat`, used by the overlay, and
`/api/context/analyze`, which is implemented but is not currently called by
the popup or overlay. Likewise, `frontend/src/content.ts` defines a context
extractor, but no current frontend module imports or invokes it.

## 2. React popup

### `frontend/src/main.tsx` — React bootstrapping

- `import { StrictMode } from 'react'` imports React's development helper.
  Strict Mode can surface lifecycle issues during development; it does not
  create another production UI.
- `import { createRoot } from 'react-dom/client'` imports React's modern DOM
  mounting API.
- `import './index.css'` loads the global reset, typography, and theme styles
  before rendering.
- `import App from './App.tsx'` loads the popup's top-level component.
- `document.getElementById('root')!` finds the mount node created in
  `frontend/index.html`. The `!` is TypeScript's non-null assertion: the code
  assumes the HTML always contains that element.
- `createRoot(...).render(...)` tells React to manage that DOM node and render
  the app there.
- `<StrictMode><App /></StrictMode>` wraps the app in the development checks
  described above.

### `frontend/src/App.tsx` — popup state and actions

#### Imports and tab type

- `useEffect` and `useState` are React hooks. The first runs a one-time
  restoration procedure when the popup mounts; the second stores popup UI
  state.
- `./App.css` adds the popup component's styles.
- `ChromeTab` describes the subset of a Chrome tab used here. `id` and `url`
  are optional because Chrome may return a tab with either missing.

#### Component state

- `function App()` defines the popup component.
- `enabled` starts as `false`. It controls the status copy, description, and
  button label.
- `loading` starts as `true`. While Chrome storage/tab operations are in
  progress, it disables the button and displays “Please wait…”.
- `error` starts empty. A non-empty string is rendered as the visible error.

The earlier callback-style storage restoration remains in the file as
commented-out code. It has no runtime effect; the active version below uses
the Promise-returning Chrome API.

#### Restore saved state and current-page overlay

- `useEffect(..., [])` runs the restoration effect once for this popup mount.
  The empty dependency array means it does not rerun when React state changes.
- `cancelled` tracks whether the popup unmounted before the asynchronous
  restoration finished.
- `restoreCopilot()` is an inner async function so the effect can use `await`
  while still returning a synchronous cleanup function to React.
- `chrome.storage.local.get('copilotEnabled')` reads the persistent extension
  setting.
- The `cancelled` check prevents a stale asynchronous result from changing
  React state after unmount.
- `stored.copilotEnabled === true` deliberately treats only the boolean
  `true` as enabled; missing or unexpected values are disabled.
- `setEnabled(isEnabled)` synchronizes the popup label with saved state.
- `if (!isEnabled) return` avoids querying tabs or injecting a script if the
  user has not enabled the feature.
- `chrome.tabs.query({ active: true, currentWindow: true })` asks Chrome for
  the active tab in the current window. Destructuring `[tab]` takes the first
  result.
- The guard requires a tab ID, URL, and an `http:` or `https:` URL. Browser
  internal pages and extension pages are not normal web pages that this
  overlay can be injected into.
- `chrome.scripting.executeScript(...)` injects the built public
  `overlay.js` file into that tab.
- The `catch` logs restoration errors to the developer console. Unlike the
  button actions, it does not put a restoration failure into the popup's
  `error` state.
- The `finally` block always clears the initial loading indicator unless the
  component has already been cancelled.
- `void restoreCopilot()` starts the promise-returning function without making
  the effect itself async.
- The cleanup function sets `cancelled = true` when React removes the popup.

#### Validate the active tab

- `getActiveTab(): Promise<ChromeTab>` centralizes active-tab lookup and
  validation for both button actions.
- It queries the active tab in the current window, using the same Chrome API
  as the restoration effect.
- If the tab has no ID or URL, or its URL is not HTTP(S), the function throws
  an actionable error message.
- Otherwise it returns only the `id` and `url` fields the caller needs. This
  narrows a large Chrome `Tab` object to the component's smaller type.

#### Enable action

- `enableCopilot()` clears an earlier error and sets `loading` before doing
  asynchronous work.
- It calls `getActiveTab()` so unsupported pages fail before script injection.
- `executeScript` injects `overlay.js` into the active page. `tab.id!` asserts
  the ID exists; the preceding helper has already checked that.
- Only after successful injection does the function save
  `{ copilotEnabled: true }` in Chrome local storage and update React state.
- If any step throws, the catch displays the thrown `Error.message`, or a
  generic message for a non-`Error` value.
- `finally` always clears the loading state, including on failure.

#### Disable action

- `disableCopilot()` follows the same clear-error / loading lifecycle.
- It validates the active tab using `getActiveTab()`.
- It runs a small function inside that page. The function finds the overlay
  section by its stable ID and removes it if present; optional chaining makes
  the operation harmless if no overlay is there.
- It then stores `copilotEnabled: false` and updates React state.
- Failure is shown in the popup, and `finally` restores the button.

The enabled flag is stored globally in extension storage, but the overlay is
injected into a particular active tab. Consequently, the persisted flag and
the set of tabs with an already-injected overlay are not exactly the same
thing. On reopening the popup while enabled, the effect injects the overlay
into whichever tab is currently active.

#### Rendered popup

- `<main className="copilot">` is the popup's outer layout container.
- The header displays a decorative star and product name/description.
- The intro row always includes the status dot and conditionally reports
  enabled or disabled from React state.
- `enable-description` also changes based on the flag to explain the current
  state.
- The primary button is disabled while loading. Its click callback calls the
  enable or disable function according to `enabled`; `void` marks the
  fire-and-forget promise explicitly.
- The button text has three states: loading, enabled (offer “Disable”), and
  disabled (offer “Enable”).
- `{error && ...}` renders the error block only when there is an error.
- The footer communicates the intended local Ollama execution model.
- `export default App` makes the component available to `main.tsx`.

### `frontend/src/App.css` — popup-specific styles

- `.suggestions` adds spacing around a suggestions region.
- `.suggestions h2` resets its heading margin and sets a compact 14px size.
- `.suggestions p` uses the muted text color and small text size.
- `.suggestion-list` lays out children in a grid with an 8px gap.
- `.suggestion-button` aligns button contents horizontally, spaces them apart,
  left-aligns text, adds padding and a border, and sets dark-theme colors and
  compact typography.
- `.suggestion-button:hover:not(:disabled)` changes the background and accent
  border only while an enabled suggestion button is hovered.
- `.page-status` uses muted small text and allows long URLs/text to wrap.
- `.enable-description` defines spacing, color, font size, and line height for
  the active popup explanation.
- `.intro .status-dot` prevents the status indicator from shrinking in a flex
  row.

The current `App.tsx` does not render `.suggestions`, `.suggestion-list`,
`.suggestion-button`, or `.page-status`; those rules are currently dormant
styles, not proof that the popup shows a suggestions list.

### `frontend/src/index.css` — global styles

- `:root` defines CSS custom properties for text, heading, background,
  borders, code backgrounds, accent colors, social backgrounds, and shadows.
- `--sans`, `--heading`, and `--mono` define reusable font stacks.
- `font: 18px/145% var(--sans)` sets the root font size, line height, and
  family; a media query reduces the base font to 16px at narrower viewport
  widths.
- `letter-spacing`, `color-scheme`, foreground/background colors, font
  synthesis, text rendering, and the two font smoothing declarations tune
  global text appearance and native control theming.
- `@media (prefers-color-scheme: dark)` replaces the main theme variables for
  a dark system preference. The nested `#social .button-icon` filter targets
  a social icon, though this selector is not used by the current popup.
- `#root` limits the main app to 1126px, keeps it responsive, centers it,
  draws inline borders, fills at least the small-viewport height, and uses a
  vertical flex layout. The popup itself is narrower than this maximum.
- `body { margin: 0 }` removes the browser's default page margin.
- `h1, h2` share the heading font, weight, and high-contrast color.
- The `h1` and `h2` blocks define sizes, spacing, line height, and letter
  spacing; both include smaller-screen adjustments.
- `p { margin: 0 }` removes default paragraph margins.
- `code, .counter` share monospace styling, inline-flex layout, rounded
  corners, and heading color. `code` then gets its own size, padding, and
  background.

### `frontend/index.html` — Vite/extension document shell

- `<!doctype html>` enables standards-mode HTML.
- `<html lang="en">` declares the document language.
- The charset meta tag sets UTF-8.
- The favicon link points at the public SVG asset.
- The viewport meta tag makes the popup layout use the device width.
- `<title>frontend</title>` is the current document title; it is still a
  generic template title.
- `<div id="root"></div>` is the DOM mount target used by `main.tsx`.
- The module script loads `/src/main.tsx`; Vite transforms TypeScript and JSX
  for development/build output.

### `frontend/src/content.ts` — page-context helper (currently unused)

- `PageContext` defines the JSON-like structure accepted by the backend:
  `page_title`, `page_url`, and `page_text`, all strings.
- `extractPageContext()` returns the current browser document's title, URL,
  and visible body text.
- A missing/empty title falls back to “Untitled page”.
- `document.body?.innerText ?? ''` safely reads visible text when the body
  exists and otherwise uses an empty string.
- `.slice(0, 20000)` caps collected text at 20,000 characters, matching the
  backend's maximum page-text size.

The active injected overlay duplicates this extraction logic in its own
file. This helper is not imported by the React popup, and importing it there
would not itself grant access to a webpage's DOM.

## 3. Chrome extension scripts and configuration

### `frontend/public/manifest.json` — extension declaration

- `manifest_version: 3` selects Chrome's current Manifest V3 extension
  model.
- `name`, `version`, and `description` identify the extension in Chrome.
- `permissions` requests:
  - `activeTab` for temporary access to the user-selected active tab,
  - `scripting` to inject scripts into eligible pages, and
  - `storage` for the persisted enabled flag.
- `host_permissions` allows the extension background worker to call the local
  backend at `http://127.0.0.1:8000/`.
- `action.default_title` sets the toolbar tooltip.
- `action.default_popup` opens the built `index.html` when the toolbar icon is
  clicked.
- `background.service_worker` points at the message-handling worker. The
  formatting of this JSON object is unusual but the properties are valid.

### `frontend/public/overlay.js` — injected page panel

#### Constants and setup

- The immediately invoked arrow function wraps the implementation in a
  private scope, avoiding global variables on the page.
- `ROOT_ID` gives the panel a stable DOM ID, used to prevent duplicates and to
  remove the panel.
- `MIN_REFRESH_INTERVAL` sets a 45-second limit for ordinary (non-forced)
  suggestions.
- `DEBOUNCE_MS` waits 2.5 seconds after page mutations before checking for a
  refresh.
- `MAX_PAGE_TEXT` limits captured visible text to 20,000 characters.
- The early `getElementById` return prevents injecting a second copy of the
  overlay into the same document.
- `document.createElement('section')` creates the panel root; assigning its
  ID and accessible label gives it a stable identity and a screen-reader
  label.
- `root.style.cssText` sets fixed positioning at the bottom-right, a bounded
  responsive width and height, scrolling, a very high stacking order, dark
  colors, a border, rounded corners, shadow, and system font.

#### Panel markup and DOM references

- `root.innerHTML` creates the panel structure: heading, LIVE status, close
  button, description, suggestion area, “Suggest now” and “Pause” buttons,
  answer region, and local-model footer.
- The suggestion and answer containers have `aria-live="polite"` so assistive
  technology can announce updates without interrupting the user.
- `document.documentElement.appendChild(root)` attaches the panel to the
  document so it appears above the page.
- `querySelector` stores references to the suggestion, answer, status, and
  action controls. Those references are reused instead of repeatedly
  searching the DOM.

The static HTML is authored by the extension itself. AI-generated text is
later assigned with `textContent`, not interpolated into `innerHTML`, so
model output is displayed as text rather than interpreted as markup.

#### Runtime state and page context

- `paused` records whether automatic refreshes should stop.
- `stopped` marks a closed panel so asynchronous work and observer callbacks
  can exit.
- `busy` prevents concurrent AI requests.
- `debounceTimer` stores the pending DOM-mutation timer.
- `lastRequestAt` records the time the last AI request started.
- `lastObservedText` stores the last page-text snapshot used for change
  detection.
- `requestVersion` marks each request generation; it helps stale results avoid
  overwriting newer state.
- `readPageContext()` reads the current title, URL, and visible body text,
  applying the 20,000-character cap.
- `setStatus()` updates the status label text and optional color.

#### Request a suggestion

- `requestSuggestion(force = false)` is asynchronous; callers can bypass the
  normal interval by passing `true`.
- The first guard exits if the panel was closed, paused, or is already
  waiting on a request.
- It reads the current time. If this is not a forced request and the last
  request was less than 45 seconds ago, it exits.
- It collects current page context. If the page has fewer than 80 non-whitespace
  characters, it displays a waiting message and does not call the backend.
- It marks itself busy and records the request start time.
- It increments `requestVersion` and saves that value for this request.
- The refresh button is disabled and relabeled “Thinking…”, status changes to
  THINKING, and the suggestion box gets progress text.
- `chrome.runtime.sendMessage(...)` sends a `COPILOT_CHAT` message to the
  extension worker with the current context and a generated question prompt.
- The prompt asks for one concise, specific next action; provides examples;
  asks the model not to invent facts; and explicitly treats webpage text as
  untrusted content.
- After awaiting the response, the `stopped` and request-version checks discard
  results that should no longer apply.
- A returned `error` is converted into a thrown `Error`. Missing answer data
  is also treated as an error, rather than shown as an empty successful
  suggestion.
- A valid answer is assigned to `suggestionElement.textContent`. The answer
  panel is hidden and status returns to LIVE.
- The catch displays a useful error in the suggestion box only if this
  request is still current and the panel is still open. Status becomes RETRY.
- `finally` clears the busy flag and restores the refresh button for the
  current request.

#### Detect page changes and button interactions

- `scheduleRefresh()` exits when the panel is closed or paused.
- `clearTimeout` resets any previous scheduled check, implementing the
  debounce so rapid DOM changes do not trigger a request per mutation.
- After 2.5 seconds it rereads page text.
- The first comparison/comment is intended to ignore tiny/no-op mutations.
  Its length-difference test is combined with exact equality, so in effect it
  ignores the case where text is unchanged and the length difference is below
  100; the following exact-equality check also ignores unchanged text of any
  size.
- If the text has changed, it updates `lastObservedText` and forces a
  suggestion. Forced refresh bypasses the 45-second interval, but the `busy`
  guard still blocks overlapping requests.
- The refresh click listener explicitly forces a new suggestion.
- The pause listener toggles `paused`, changes the button label, clears a
  pending timer, and shows PAUSED status. Resuming snapshots the current text,
  resets LIVE status, and forces a suggestion.
- The close listener marks the panel stopped, increments the request version
  to invalidate pending responses, clears the timer, disconnects the observer,
  removes the panel, and stores the disabled flag.

#### Mutation observer and initial request

- `MutationObserver` watches page DOM changes.
- Its callback ignores work after close or while paused.
- It checks the mutation targets and ignores mutations whose target is inside
  the overlay, preventing the panel's own text changes from recursively
  triggering page refreshes.
- If any relevant page mutation exists, it schedules the debounced check.
- The initial `lastObservedText` is set before observing, establishing a
  baseline.
- The observer watches `document.body` (or the document element fallback),
  including descendants, child-list changes, and text-node changes.
- The final forced request immediately tries to produce the first suggestion.

### `frontend/public/service-worker.js` — backend bridge

- `chrome.runtime.onMessage.addListener(...)` registers the extension
  message handler.
- Messages other than `COPILOT_CHAT` are ignored by returning without a
  response.
- The sender guard requires the message to come from this extension and from
  a browser tab. Requests that fail it receive `Unauthorized request.` and
  stop before network access.
- `fetch('http://127.0.0.1:8000/api/chat', ...)` makes an HTTP POST to the
  local FastAPI backend.
- The request header declares JSON, and `JSON.stringify(message.payload)`
  serializes the overlay's context and question into the request body.
- The `.then` handler parses the JSON response.
- A non-2xx response becomes an error using the API's `detail` field when
  available.
- A successful response is returned to the sender as `{ data }`.
- The `.catch` converts a network/API error into a message object. This lets
  the overlay show a visible failure instead of waiting indefinitely.
- `return true` tells Chrome that `sendResponse` will be called
  asynchronously after the fetch completes.

### `frontend/vite.config.ts` and `frontend/package.json`

- `vite.config.ts` imports Vite's `defineConfig` helper and the React plugin.
- `plugins: [react()]` configures React/JSX transformation.
- `base: './'` makes generated asset paths relative, useful when the built
  popup is loaded as an extension page rather than hosted at a website root.
- `package.json` names this private frontend package and declares ES module
  semantics with `"type": "module"`.
- `dev` runs Vite's development server.
- `build` runs TypeScript project builds first, then creates production output
  with Vite.
- `lint` runs ESLint over the frontend package.
- `preview` serves the already-built frontend locally for preview.
- Runtime dependencies are React and React DOM. The dev dependencies include
  TypeScript, Vite, the React Vite plugin, Chrome typings, and ESLint plugins
  and configurations.

The `frontend/public` directory is copied into the Vite build's output. This
is how the manifest, overlay, and service worker are made available beside
the popup HTML in an extension package.

### `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, and `frontend/tsconfig.node.json`

- The root `tsconfig.json` contains no source files itself. Its `references`
  point TypeScript's build mode at the separate browser-app and Node/Vite
  configurations.
- In `tsconfig.app.json`, `tsBuildInfoFile` places incremental compiler state
  under `node_modules/.tmp`.
- `target: "es2023"` and `lib: ["ES2023", "DOM"]` select modern JavaScript
  features and browser APIs for frontend source.
- `types` loads Vite client declarations and Chrome extension API
  declarations, which is why `chrome.*` calls are recognized by TypeScript.
- `skipLibCheck` avoids type-checking declaration files from dependencies.
- `moduleResolution: "bundler"` matches Vite's module resolution;
  `allowImportingTsExtensions` permits explicit TypeScript extensions;
  `verbatimModuleSyntax` preserves import/export intent; and
  `moduleDetection: "force"` treats files as modules.
- `noEmit` means TypeScript checks the code but leaves JavaScript emission to
  Vite. `jsx: "react-jsx"` uses React's automatic JSX runtime.
- `noUnusedLocals` and `noUnusedParameters` catch unused declarations;
  `erasableSyntaxOnly` limits TypeScript syntax to constructs erasable before
  runtime; and `noFallthroughCasesInSwitch` guards switch control flow.
- `include: ["src"]` scopes the browser project to application source.
- `tsconfig.node.json` uses a separate incremental build-info file, ES2023
  library, Node types, and `nodenext` module mode for the Vite config.
- It repeats the no-emit and code-quality options and includes only
  `vite.config.ts`, so browser-only globals and Node tooling types stay
  separated.

### `frontend/eslint.config.js` — lint rules

- Imports the base JavaScript rules, browser global names, React Hooks rules,
  React Fast Refresh rules, TypeScript ESLint configuration, and ESLint's
  flat-config helpers.
- `defineConfig([...])` exports the flat configuration.
- `globalIgnores(['dist'])` excludes generated build output.
- The config applies to `.ts` and `.tsx` files.
- The `extends` list enables recommended JavaScript and TypeScript rules,
  hook correctness checks, and Vite/React Fast Refresh checks.
- `languageOptions.globals: globals.browser` makes browser APIs known to
  ESLint. Chrome-specific types are supplied separately through TypeScript.

### Frontend assets and template README

- `frontend/public/favicon.svg` is the favicon referenced by `index.html`.
- `frontend/public/icons.svg` is an SVG symbol sprite containing social,
  documentation, and other icon symbols. The current React popup does not
  reference those symbols.
- `frontend/src/assets/hero.png`, `react.svg`, and `vite.svg` are source
  assets, but none are imported by the current popup implementation.
- `frontend/README.md` is the stock React/Vite template guide; it describes
  template capabilities rather than documenting this extension's runtime.

## 4. FastAPI backend

### `backend/app/main.py` — HTTP API

#### Imports and application instance

- `FastAPI` creates the ASGI application and `HTTPException` provides
  intentional HTTP error responses.
- `BaseModel` and `Field` define and validate request bodies.
- `get_ai_provider` obtains the local Ollama provider implementation.
- `app = FastAPI(...)` creates the application object that an ASGI server
  serves.
- `title`, `description`, and `version` supply API metadata and appear in
  generated OpenAPI documentation.

#### Request models

- `ContextRequest` is the body schema for context analysis.
- `page_title` defaults to “Untitled page” and is limited to 500 characters.
- `page_url` defaults to an empty string and is limited to 2,048 characters.
- `page_text` is required, must contain at least one character, and is capped
  at 20,000 characters.
- `ChatRequest` is the body schema for chat.
- `question` is required, non-empty, and capped at 4,000 characters.
- Its page title, URL, and text use the same defaults/limits as above, except
  chat page text can be empty by default.

Pydantic validates these values before the endpoint runs. Invalid bodies are
rejected with FastAPI's standard validation response, rather than being sent
to Ollama.

#### Health routes

- `@app.get("/")` binds `root()` to the root GET route.
- `root()` returns a small JSON object with a human-readable message and
  `"status": "ok"`.
- `@app.get("/health")` binds the dedicated health-check route.
- `health_check()` returns a status and service identifier. Neither health
  endpoint invokes the model, so it checks the API process, not Ollama
  availability.

#### Analyze context endpoint

- `@app.post("/api/context/analyze")` registers a POST endpoint.
- FastAPI parses and validates the JSON body into `ContextRequest`.
- The multiline `prompt` asks the model to summarize the page, produce three
  to five important points, and propose one follow-up question.
- The prompt includes title and URL plus the page text inside
  `<page_content>` tags.
- Its instructions explicitly state that page content is untrusted and must
  not be treated as instructions. Delimiters and wording help the model
  distinguish supplied page data from the task prompt.
- In the `try` block, `get_ai_provider()` creates a provider and
  `generate(prompt)` performs inference.
- The success response includes the original title and the model text under
  `summary`.
- If provider construction or inference raises an exception, the endpoint
  returns HTTP 503 and a message directing the user to check Ollama.

This route exists in the backend, but there is no current call to it in the
extension flow described above.

#### Chat endpoint

- `@app.post("/api/chat")` registers the endpoint used by the service worker.
- The validated body is provided as `ChatRequest`.
- The prompt asks the model to answer the user's question with the page as
  context where relevant.
- It repeats the untrusted-page instruction and asks the model to admit when
  an answer is unavailable instead of making up facts.
- Title, URL, and page text are inserted into the page context section.
- The question is separately delimited under `<user_question>`.
- Inference follows the same provider creation and `generate()` call.
- Success returns `{"answer": result}`, which matches the overlay's expected
  `result.data.answer` shape after the worker wraps the API response in
  `{ data }`.
- Errors become HTTP 503 with the local-model-unavailable detail. The worker
  reads that detail and forwards it to the overlay.

The exception handler intentionally translates provider errors into an API
response. Because it catches all exceptions, the API response does not expose
the underlying exception details; debugging detail is not currently logged
here.

### `backend/app/services/ai_provider.py` — local Ollama adapter

- `os` reads environment-variable configuration.
- `ollama` is the Python Ollama client package.
- `OllamaProvider` groups model configuration, the client, and generation
  into a small provider interface.
- `__init__` reads `OLLAMA_MODEL`, defaulting to `qwen2.5:7b`.
- It creates `ollama.Client` with `OLLAMA_HOST`, defaulting to
  `http://127.0.0.1:11434`.
- `generate(prompt)` calls the client's `generate` method with the configured
  model and supplied prompt.
- `response.response.strip()` extracts the generated text and removes
  whitespace at its ends.
- `get_ai_provider()` returns a newly constructed `OllamaProvider`; there is
  no singleton/cache, so each endpoint invocation creates a client instance.

### `backend/app/__init__.py`

This file is empty. Its presence marks `app` as a Python package in layouts
that rely on regular packages rather than implicit namespace packages.

## 5. Backend checks and local infrastructure

### `backend/test_ai_provider.py`

- Imports `get_ai_provider` from the application package.
- `main()` obtains the configured provider and prepares a sample prompt about
  Python.
- It prints a progress message, invokes `generate`, and prints the response.
- The `if __name__ == "__main__"` guard makes the sample run only when this
  file is executed directly, not when imported.

This is an integration/smoke script: it requires a reachable Ollama service
and the configured model. It is not a mocked unit test.

### `backend/test_connections.py`

- Imports environment access, Redis, PostgreSQL's `psycopg`, and Kafka's
  `KafkaProducer` clients.
- `test_redis()` connects to local Redis, writes a short-lived key, reads it
  back, asserts the value, prints success, and closes the client.
- `test_postgres()` requires `POSTGRES_PASSWORD`; if absent it raises a clear
  setup error. It connects to the local `copilot` database as user `copilot`,
  executes `SELECT 1`, asserts the result, and prints success. The `with`
  blocks close the connection and cursor when complete.
- `test_kafka()` constructs a producer against local port 9092 with bounded
  connection timeouts and closes it after connection setup.
- The `__main__` block runs each check in sequence and prints a final success
  message only if all prior operations succeed.

These checks require the corresponding local services to be running. They
are separate from the FastAPI request path; the current API code does not
read or write Redis, PostgreSQL, or Kafka.

### `docker-compose.yml`

- `services` defines local infrastructure containers.
- `redis` uses the small Redis 7 Alpine image, maps Redis only to loopback
  (`127.0.0.1:6379`), persists data in `redis_data`, enables append-only
  persistence, restarts unless explicitly stopped, and checks readiness with
  `redis-cli ping`.
- `postgres` uses PostgreSQL 17 Alpine, creates the `copilot` database/user,
  requires `POSTGRES_PASSWORD` from a `.env` file, binds only to loopback
  port 5432, persists its data, and uses `pg_isready` for its health check.
- `kafka` uses Apache Kafka 4.1.1 in a single-node broker/controller setup.
  It exposes the client port on loopback, configures the controller quorum
  and single-node replication settings, persists Kafka data, and restarts
  unless stopped.
- The top-level `volumes` declarations create persistent storage for the
  three services.

The Compose file does not define the FastAPI server or Ollama. Redis,
PostgreSQL, and Kafka are currently infrastructure available for development
and connection checks, but no shown backend route uses them.

## 6. End-to-end behavior and practical limitations

1. Clicking the toolbar action opens the React popup declared in the manifest.
2. The popup reads `copilotEnabled`; if true, it injects the overlay into the
   currently active HTTP(S) tab.
3. Enabling validates the current tab, injects the overlay, then persists
   `copilotEnabled: true`.
4. The overlay immediately captures the page and sends an initial proactive
   prompt through extension messaging.
5. The service worker posts that payload to `/api/chat`.
6. FastAPI validates it, builds a prompt, and asks Ollama to generate text.
7. The worker returns the answer to the overlay, which inserts it as text.
8. DOM changes are debounced and can trigger another forced suggestion.
9. Pausing suppresses automatic and button-triggered calls until resumed.
   Closing removes the overlay and persists the disabled flag.

Important implementation boundaries:

- Only HTTP(S) pages are eligible for injection.
- Page text is capped in both the injected script and API schema.
- `activeTab` and `scripting` permissions control injection; host permission
  is granted only for the local API address.
- The overlay does not currently display a separate answer/chat form; the
  `answer` element is hidden after valid suggestions and there is no current
  UI path that populates it.
- There is no active frontend caller for `/api/context/analyze`.
- The app says “Private, local AI assistance” and uses loopback URLs, but page
  content is still sent to the local backend/model process. Users should
  enable the feature only on pages whose content they are comfortable
  processing locally.
- The frontend has Vite scripts in `package.json`; the backend's server
  launch command and Python dependency manifest are not included in the
  inspected project files.
