# مساعد الدراسة — Arabic CS Study Helper

[![tests](https://github.com/younislayan/study-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/younislayan/study-helper/actions/workflows/tests.yml)

A chat app that explains computer science topics in clear Arabic, built for Arabic-speaking university students.

**Live:** https://younislayan.github.io/study-helper/

Most good CS explanations online are in English. Students who think in Arabic often understand a topic much faster when it's explained in their own language — but with the technical terms kept in English, because that's how they appear in code, exams and jobs. This app does exactly that.

## Features

- **Answers in Arabic, terms in English** — *pointer*, *recursion*, *thread* stay in English, the way Arab developers actually say them; code is always in English
- **Three modes**
  - **اشرح** (Explain) — the core idea first, then step by step
  - **أعطني مثال** (Give me an example) — a worked example, explained line by line
  - **اختبرني** (Quiz me) — asks one question at a time and gives feedback on each answer
- **Streaming** — answers appear word by word as they're generated
- **Remembers the conversation** — follow-up questions work
- **Right-to-left layout**, light and dark mode, works on phones

## How it works

It's a single HTML file with no server and no build step.

- The page uses the official [Anthropic TypeScript SDK](https://github.com/anthropics/anthropic-sdk-typescript), loaded from a CDN, to call **Claude Opus 5** directly from the browser.
- A **system prompt** defines the tutor's behaviour: language, tone, how to handle technical terms. Each mode adds one extra instruction on top.
- The whole conversation is sent with every request, so Claude has the context for follow-up questions.
- Responses are **streamed**, and the page re-renders the text as each piece arrives.
- Server-side **fallbacks** are enabled, so if a request is declined by the main model, Anthropic automatically retries it on another Claude model.

## Your API key

The app needs a Claude API key from [platform.claude.com](https://platform.claude.com). You enter it in the app; it's stored **only in your own browser** and sent only to Anthropic. It is never in this repository.

Calling the API straight from a browser is fine for a personal tool like this, where each person uses their own key. A public app with a shared key would need a small server to keep the key secret.

## Tests

End-to-end tests with **Playwright (Python)**, run automatically on every push by GitHub Actions.

The Claude API is intercepted and answered with a recorded streaming response, so the suite is
deterministic, needs no API key and costs nothing to run. 13 tests cover:

- the welcome screen and example questions
- asking without a key opens the key dialog and sends nothing
- a streamed answer is displayed, and Markdown (headings, bold, code blocks) is rendered as HTML
- API errors map to the right Arabic message (invalid key, rate limit)
- conversations are saved, survive a page reload, and can be reopened and deleted
- answer modes change what is sent to the model

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest tests -q
```

## Built with

HTML · CSS · JavaScript · Claude API (Anthropic SDK) · Playwright · pytest · GitHub Actions

---

Made by [Layan Younis](https://younislayan.github.io)
