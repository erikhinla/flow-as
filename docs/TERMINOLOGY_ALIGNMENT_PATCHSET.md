# Terminology Alignment Patchset

To maintain canon across the execution ecosystem, this patchset outlines the required terminology replacements and updates across `flow-as` and associated properties.

## Canonical Rules

| Approved Canonical Term | Rejected Alternative / Legacy Term | Description / Usage Context |
|---|---|---|
| **FLOW** | FLOW (without definition), Uncapitalized "flow" | Acronym for "Frictionless Leveraged Orchestrated Workflows". Use in brand docs, repos, external copy. |
| **FLOW Agent Architected Schemas (FAAS)** | FLOW Agent OS, FLOW Agent AS | The primary system name across README, deployment pages, and press kits. |
| **Execution Engine** | runtime (when used as a proper noun system name) | Functional role identifier. Use in architecture docs and control-plane descriptions. |
| **quad-kernel keystone** | framework pieces, ad hoc setup | Refers to: folders, markdowns, scripts, protocols. |
| **INFRA4ALL** | Inconsistent hashtag variants | Social assets, manifesto, and template platforms. |
| **layers** | plates | Used in diagnostics, routing logic, and architecture maps. Avoid introducing the term "plates". |
| **BizBot Mktng** | BizBot Marketing, BizBot | Must be used on offer pages, CTAs, and checkout surfaces. |

## Execution Checklist

- [ ] Search and replace "FLOW Agent OS" with "FLOW Agent Architected Schemas (FAAS)" in `README.md`.
- [ ] Search and replace "FLOW Agent AS" with "FLOW Agent Architected Schemas (FAAS)" in `docker-compose.yml` comments and `DEPLOYMENT.md`.
- [ ] Search and replace standalone mentions of "runtime" (used as a system name) with "Execution Engine" across all `.md` files in `docs/`.
- [ ] Update any references of "BizBot Marketing" to "BizBot Mktng" within the `BIZBUILDERS` assets.
- [ ] Ensure "layers" is used consistently in `docs/EXECUTABLE_DIAGNOSTIC_SYSTEM_LAYOUT.md` and no usage of "plates" exists.

*Note: Proceed with executing these search-and-replace updates on a feature branch to avoid unintended code string mutations before submitting to main.*
