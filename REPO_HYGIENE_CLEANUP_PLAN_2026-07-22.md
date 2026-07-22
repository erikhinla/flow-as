# Repo Hygiene Cleanup Plan

Date: 2026-07-22

## Plain-English Read

The repo is noisy because production website files, raw creative assets, worker/runtime files, reports, archives, experiments, and generated outputs are all living in one place.

That does not mean everything is bad. It means the repo no longer has clean lanes. A future change can accidentally scoop up old files, secrets, drafts, broken experiments, or giant media assets.

The launch website is now committed separately. Do not run broad cleanup against it until the current production state is safely pushed and verified.

## Current Shape

- Git root: `/Users/test/Documents/Documents - E$ COMPUTAAA/flow-as copy`
- Live site source: `/Users/test/Documents/Documents - E$ COMPUTAAA/flow-as copy/launch`
- Current launch commit: `db4fe4d`
- Biggest folders:
  - `.git`: about 2.5 GB
  - `assets`: about 1.2 GB
  - `launch`: about 1.1 GB
  - `services`: about 121 MB
- Current working tree:
  - 279 modified files
  - 12 deleted files
  - 162 untracked files

## What Belongs Where

### Keep Active

These should stay easy to find and safe to build from.

- `launch/`: production TransformBy10X website
- `services/`: active application/service code only
- `schemas/`: active contracts only
- `scripts/`: active operational scripts only
- `.github/`: active workflows and agent instructions only
- `README.md`, `DEPLOYMENT.md`: current repo docs only

### Archive

These may still matter, but they should not sit in the active work path.

- `_ARCHIVE/`
- `FAAS_ARCHIVE/`
- `FLOW_AGENT_AS_DUPLICATE/`
- `Users_DUPLICATE/`
- old launch reports
- old one-off PDFs
- old campaign exports
- old screenshots
- old mockup zips

Archive target should be outside this repo or in one clearly named cold-storage folder.

### Ignore

These are generated, temporary, local, or too easy to accidentally commit.

- `.DS_Store`
- `.venv/`
- `.vercel/`
- `__pycache__/`
- `.swp`
- `tmp/`
- `scratch/`
- `output/`
- `generated/`
- `runtime/queues/`
- `runtime/logs/`
- `storage/artifacts/`
- `launch/output/`
- `launch/verification-screenshots/`
- old local package zips
- local SSH keys or credentials

### External Asset Library

Raw creative assets should not all live in Git.

Move these to an external media library and keep only final optimized site assets inside `launch/assets/`.

- raw MP4 exports
- huge mockup zips
- source PDFs
- unused Canva/Midjourney outputs
- screenshots used for review only
- duplicate video formats

## Cleanup Phases

### Phase 1: Protect The Launch State

Goal: make the current launch website safe.

- Push commit `db4fe4d` to GitHub after auth is fixed.
- Confirm the branch exists remotely.
- Confirm production still serves:
  - `/`
  - `/diagnostic`
  - `/fog-free-daily`
  - `/bizbuilders-ai`
  - `/bizbot-mrktng`

### Phase 2: Stop Future Noise

Goal: prevent new accidental mess.

- Strengthen `.gitignore`.
- Add a local exclude for secrets.
- Confirm local SSH keys are not inside the repo.
- Ignore generated reports, screenshots, temp folders, and old package zips.

### Phase 3: Separate Live Site From Source Assets

Goal: make `launch/` obvious and deploy-safe.

- Keep only used website files in `launch/`.
- Move unused social/campaign/source assets out of `launch/assets/`.
- Keep production-ready media only.
- Keep a small asset manifest that says what each active asset does.

### Phase 4: Archive Old Systems

Goal: stop old FLOW/OpenClaw/FAAS work from polluting current launch work.

- Move duplicate folders to cold storage.
- Remove deleted duplicate paths from active Git history in a dedicated cleanup commit.
- Keep one current operations folder for active worker/service work.

### Phase 5: Service Repo Review

Goal: decide whether this should remain one repo.

Recommended split:

- `transformby10x-site`: production website
- `flow-as`: automation/workers/runtime
- `tbtx-assets`: media library or external storage

If keeping one repo, use clear top-level lanes:

- `launch/`
- `services/`
- `ops/`
- `docs/`
- `assets-final/`
- `archive/`

## First Safe Cleanup Pass

Do this only after the launch commit is pushed.

1. Update ignore rules.
2. Remove local key files from repo path.
3. Delete editor junk like `.swp`.
4. Move old package zips out of `launch/assets/downloads/`.
5. Move unused campaign/source media out of `launch/assets/`.
6. Keep only final website media required by deployed pages.
7. Commit cleanup as `Quiet generated files and local artifacts`.

## Do Not Do

- Do not run `git add -A` from repo root.
- Do not delete raw creative assets without moving them somewhere safe first.
- Do not mix website launch commits with repo cleanup commits.
- Do not remove runtime/service files until their current purpose is verified.
- Do not treat a folder as junk just because the name looks old.

## Working Definition

Quiet means:

- a visitor-facing site file is easy to find
- a deploy uses only intended files
- a commit contains one kind of work
- generated files do not appear in status
- raw assets do not drown the codebase
- old experiments cannot be mistaken for current product

