# Resources Folder

This folder contains static assets for the UI application.

## Image Files

### profile.png
- **Size:** 48x48 pixels recommended (will be scaled automatically)
- **Format:** PNG with transparency support
- **Purpose:** User profile picture displayed in the user profile widget
- **Fallback:** If not present, displays emoji avatar

### logo.png
- **Size:** 32px height recommended (width will scale proportionally)
- **Format:** PNG with transparency support
- **Purpose:** Application logo displayed in the title bar
- **Fallback:** If not present, only app title is shown

## Notes
- All images support transparency (PNG format recommended)
- Images are automatically scaled to fit their containers
- If images don't exist, the app gracefully falls back to text/emoji
- Place image files directly in this folder (no subdirectories needed)
