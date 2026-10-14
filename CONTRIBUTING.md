# Contributing

Thanks for helping. This repo is a Claude Code plugin, so most changes are Markdown
(skills, commands) or small stdlib scripts. The rules below keep it stable for everyone
who has it installed.

## Workflow

1. Branch from `main`: `feat/short-name`, `fix/short-name` or `docs/short-name`.
2. Make the change. Keep each pull request to one idea.
3. Run the checks locally (below).
4. Open a pull request. Its title must follow
   [Conventional Commits](https://www.conventionalcommits.org), because the title becomes
   the squash-merge commit message:
   - `feat: add vertical 1080x1920 template` adds something people can use (minor release)
   - `fix: clamp contact sheet timestamps` fixes a bug (patch release)
   - `docs:`, `chore:`, `ci:`, `refactor:` change nothing for users (no release)
   - Add `!` (`feat!:`) or a `BREAKING CHANGE:` footer when existing projects or commands
     stop working the old way (major release)
5. CI must pass. Pull requests are squash-merged and the branch is deleted.

`main` is protected: no direct pushes and no force pushes.

## Checks

```sh
python3 scripts/validate.py                       # manifests, skill and command front matter
ruff check .                                      # Python lint (pip install ruff)
shellcheck motion-video/scripts/*.sh              # Bash lint
npx markdownlint-cli2 "**/*.md"                   # Markdown lint
cd motion-video/templates/square-loop && npx hyperframes lint
```

CI runs all of these, plus a draft render of each template.

## Releases

[release-please](https://github.com/googleapis/release-please) handles versions. After
changes land on `main`, it opens a release pull request that bumps the version in
`motion-video/.claude-plugin/plugin.json` and `version.txt` and updates `CHANGELOG.md`.
Merging that pull request tags the release, publishes it, and attaches sample renders of
the templates. Don't edit versions or the changelog by hand.

GitHub doesn't run workflows on pull requests opened by GitHub Actions, so the release
workflow starts CI on the release pull request itself and checks its title. Give it a
few minutes after the release pull request appears before merging. If the release pull
request says it's out of date with `main`, click **Update branch** (rebase). That reruns
the checks normally, because the update comes from you.

## Writing skills

- Front matter needs `name` (matching the folder) and a `description` that says when to
  use the skill. Claude reads the description to decide whether to load it.
- Write instructions plainly, as steps. Put long reference material in `references/`.
- Refer to scripts as `<base dir>/../../scripts`, and never use absolute paths.
- Keep examples fictional. Don't commit client names, logos, photos or audio.

## Templates

A template must render without edits, pass `hyperframes lint` with 0 errors, and include
a `TEMPLATE.md` whose first line describes it. Audio in templates must be generated or
rights-free.
