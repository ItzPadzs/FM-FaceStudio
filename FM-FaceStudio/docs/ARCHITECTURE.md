# Architecture

FM FaceStudio separates the desktop UI from game-file parsing and analysis.

- **UI:** PySide6 pages and windows
- **AI:** game-independent face descriptors
- **FM:** game installation discovery and future version adapters
- **Assets:** indexing and searching appearance assets
- **Mesh:** read-only decoding, validation and preview
- **Projects:** `.facestudio` project persistence
- **Utils:** settings, logging and application paths

## Safety rule

No code may modify a Football Manager installation until tested backup, validation and restore workflows exist.
