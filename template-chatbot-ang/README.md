# Template Chatbot (Angular)

Port of the `template-chatbot` experience powered by Angular standalone components. The UI, quick actions, and smart home visualizations mirror the React/Vercel AI SDK preview template while remaining framework-agnostic.

## Getting started

```bash
npm install
npm run start
```

The dev server listens on `http://localhost:4200/`.

## Features

- Tailwind driven layout that reproduces the original landing hero, chat stream, and quick actions.
- Reusable components for messages, hub summaries, camera cards, and usage charts (each with dedicated folders and HTML/CSS/TS files as requested).
- `AiService` that keeps hub state, interprets natural commands (view cameras, show hub, manage lights/locks/climate, show usage) and returns the right UI blocks.

## Environment notes

- Images and fonts were copied from the original template into `src/assets`.
- Tailwind is configured via `tailwind.config.js` and used across all Angular templates.
- The service currently performs keyword-based intent detection so the experience works out-of-the-box without exposing API keys. Wire it up to a backend LLM if you prefer fully dynamic conversations.
