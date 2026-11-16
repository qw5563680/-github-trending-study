<p align="center">
  <img src=".github/assets/banner.webp" alt="Plannotator" width="640" />
</p>



<p align="center">
  <strong>Everything you need to annotate and stay in the loop with your agents</strong><br/>
  <strong>Inbox Surface • Artifacts • Code Review</strong><br/>
  <sub>Annotate plans, specs, markdown, HTML, and other interactive artifacts. Review diffs and PRs. Send feedback to your agent.</sub>
</p>

<p align="center">
  <img src=".github/assets/icons/amp.svg" alt="Amp" title="Amp" height="28" />&nbsp;&nbsp;
  <img src=".github/assets/icons/claude.svg" alt="Claude Code" title="Claude Code" height="28" />&nbsp;&nbsp;
  <img src=".github/assets/icons/codex.png" alt="Codex" title="Codex" height="28" />&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/icons/copilot-dark.svg" />
    <img src=".github/assets/icons/copilot-light.svg" alt="Copilot CLI" title="Copilot CLI" height="28" />
  </picture>&nbsp;&nbsp;
  <img src=".github/assets/icons/droid.png" alt="Droid" title="Droid" height="28" />&nbsp;&nbsp;
  <img src=".github/assets/icons/gemini.png" alt="Gemini CLI" title="Gemini CLI" height="28" />&nbsp;&nbsp;
  <img src=".github/assets/icons/kiro.svg" alt="Kiro" title="Kiro" height="28" />&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/icons/opencode-dark.svg" />
    <img src=".github/assets/icons/opencode-light.svg" alt="OpenCode" title="OpenCode" height="28" />
  </picture>&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/icons/pi-dark.svg" />
    <img src=".github/assets/icons/pi-light.svg" alt="Pi" title="Pi" height="28" />
  </picture>
</p>

<p align="center">
  <a href="#plannotator-inbox">Plannotator Inbox</a> · <a href="https://plannotator.ai/">Official site</a> · <a href="https://plannotator.ai/code-review">Code Review</a> · <a href="https://github.com/plannotator/effective-html">Visual HTML Skills</a> · <a href="#herdr-annotate-plannotator-in-the-terminal">Herdr Annotate</a> · <a href="https://www.youtube.com/watch?v=a_AT7cEN_9I">(Legacy) Plan Mode</a>
</p>

# Plannotator

**⭐️ NEW:** [Plannotator Inbox](https://plannotator.ai/inbox/) is the missing review layer between you and multi-agent work. It surfaces decisions, prototypes, variations, plans, and everything you need to stay in the loop. Works with all coding agents and personal assistants.

Plannotator is a local, browser-based review surface for AI coding agents: Claude Code, Codex, Copilot CLI, Gemini CLI, OpenCode, Kiro, Droid, Amp, DeepSeek Harness, and Pi. Plannotator Inbox also works with personal assistants (Grok Bot, Muse, Hermes, OpenClaw).

**It plugs directly into your agent** through plugins, hooks and commands. When the agent proposes a decision, plan, html, or finishes working, the app opens in your browser and you mark it up, comment, and send feedback directly to the agent for it to act on it.

<table>
<tr>
<td width="40%" valign="middle">

### Review documents, plans, and agent messages

Annotate plans, specs, messages, html, then send the feedback to your agent. 

</td>
<td width="60%">

<img src=".github/assets/annotate.webp" alt="Annotate UI with inline annotations" width="100%" />

</td>
</tr>
<tr>
<td width="40%" valign="middle">

### Code Review

Review local changes or remote PRs. Comment on diffs, suggest code. Your comments go back to the agent. Works with Git, GitButler, Jujutsu (`jj`), Perforce (`p4`), GitHub, and GitLab.

For a big change, start a [guided review](https://plannotator.ai/code-review#guided-review): an agent sorts the diff into chapters, the most important first.

</td>
<td width="60%">

<img src=".github/assets/review.webp" alt="Code review with file tree and side-by-side diff" width="100%" />

</td>
</tr>
</table>

## Plannotator Inbox

<p align="center">
  <a href="https://plannotator.ai/inbox/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/inbox-dark.webp" />
      <img src=".github/assets/inbox-light.webp" alt="Plannotator Inbox on a desktop and a phone: threads from several agents grouped by what each needs, a question with picture choices open beside the list, and a question with an attached chart on the phone" width="720" />
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://plannotator.ai/assets/inbox-film.mp4"><strong>Watch the demo</strong></a> · <a href="https://plannotator.ai/inbox/">More on the Inbox</a> · <a href="https://plannotator.ai/docs/reference/inbox/">Docs</a>
</p>

The Plannotator Inbox is one local window where your agents leave you messages, questions, files, and guided reviews while they keep working. Answer a question with a click, annotate a file, and press Send when you can. Nothing holds an agent session open while you do, and your reply goes back to the session that asked.

```
plannotator inbox
```

Claude Code, Pi, and OpenCode connect through Plannotator's plugins, and your replies arrive as their next turn. Any other agent reaches it over MCP with `plannotator inbox mcp`, and `plannotator inbox --help` is the guide an agent reads.

## Herdr Annotate: Plannotator in the Terminal

<p align="center">
  <a href="https://github.com/plannotator/herdr-annotate">
    <img src=".github/assets/herdr-annotate-banner.svg" alt="Herdr Annotate" width="300" align="middle" />
  </a>
  &nbsp;&nbsp;
  <img src=".github/assets/herdr-annotate.png" alt="Plannotator TUI annotating a markdown folder in the terminal" width="480" align="middle" />
</p>

[Herdr Annotate](https://github.com/plannotator/herdr-annotate) brings Plannotator-style review to the terminal: annotate terminal text, review whole Markdown documents and your coding agent's replies inside [Herdr](https://herdr.dev), and send the feedback straight back to the agent as its next message. Works with Claude Code, Codex, Pi, Copilot CLI, and Droid replies. Annotations are saved in the Plannotator data directory, so terminal reviews and app reviews compound.

```
herdr plugin install plannotator/herdr-annotate
```

Prefer it standalone? [Plannotator TUI](https://github.com/plannotator/plannotator-tui) powers the document review and runs without Herdr: `brew install plannotator/tap/plannotator-tui`.

## HTML artifacts, live sites, and guided reviews

<table>
<tr>
<td width="40%" valign="middle">

### Annotate HTML artifacts and live sites

Annotate rendered HTML files, or any site running on your machine. A local address opens your app live through a local proxy: you comment on the real page, and hot reload keeps working.

`plannotator annotate http://localhost:5173`

</td>
<td width="60%">

<img src=".github/assets/html.webp" alt="Annotating a rendered HTML artifact" width="100%" />

</td>
</tr>
<tr>
<td width="40%" valign="middle">

### Guided reviews

In code review, press **Guide** (or `Cmd/Ctrl+Shift+G`) and an agent sorts the diff into chapters: the heart of the change first, then its effects, then the glue. Each chapter puts a short overview next to the real diff. Comments you leave there go back to the agent with the rest of your review. [More on guided reviews](https://plannotator.ai/code-review#guided-review)

</td>
<td width="60%">

<img src=".github/assets/guided-review.webp" alt="A guided review chapter: an overview of the change on the left, the annotatable diff on the right" width="100%" />

