// Extends app.json so the web export can be hosted under a sub-path.
//
// The Hugging Face Space serves this bundle at /app, because Gradio owns "/".
// Without baseUrl, expo-router boots at /app, matches no route and renders its
// "This screen does not exist" screen — the HTML loads fine, so only a browser
// catches it.
//
// Unset (Docker, Cloud Run, local dev) the app stays at the root as before.
module.exports = ({ config }) => ({
  ...config,
  experiments: {
    ...config.experiments,
    baseUrl: process.env.EXPO_BASE_URL || undefined,
  },
});
