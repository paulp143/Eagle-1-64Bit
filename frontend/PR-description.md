## Redesign landing page: animated hero + easier onboarding

Replaces `frontend/index.html` with a new download page. On merge, the existing `deploy-pages.yml` workflow publishes it to GitHub Pages automatically.

### What's new
- **Live hero animation:** a canvas "sortie" built from the game's own assets (Eagle-1 sprite, enemy fighter, battlefield map, explosion spritesheet). It includes a dogfight with quad-cannon fire and a recurring 500 kg bomb run.
- **Download CTA** points to `releases/latest/download/Eagle-1-Windows.zip`, so it always serves the newest release.
- **Content sections:** gameplay screenshot, the 5 mission modes, strike arsenal (charges and blast footprints), Fireteam Viper vs. Automatons, scoring.
- **Onboarding:** 3-step Windows install (Download → Extract → Launch), a SmartScreen hint for the unsigned exe, a controls cheat sheet, and run-from-source instructions for macOS/Linux.
- **Footer:** fan-project disclaimer (not affiliated with Arrowhead / Sony).

### Technical notes
- Single HTML file with inline CSS/JS and no build step. Fonts come from Google Fonts.
- New optimized assets in `frontend/assets/` (WebP for the screenshot and map). Existing assets are untouched.
- Responsive down to phone width. Respects `prefers-reduced-motion`. The animation pauses when off-screen or when the tab is hidden.
- `dev.html`, `style.css` and `main.js` are left as-is, but the new index no longer links to `dev.html`.

### To check before merging
- Version and size in the download buttons (`v0.2.0 · 39 MB`) are hardcoded. Update them with each release.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_014kWrkfC6oLee9pcn4GgU3n
