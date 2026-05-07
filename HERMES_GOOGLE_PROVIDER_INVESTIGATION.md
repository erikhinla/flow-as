# Hermes Google Provider Investigation Report

**Date:** May 5, 2026  
**Objective:** Determine direct Google Gemini API provider support in Hermes  
**User Request:** "Use the direct Google Gemini API path" instead of OpenRouter  
**Target Model:** `gemini-3.1-flash-lite-preview`

---

## Executive Summary

**RESULT: HERMES LACKS DIRECT GOOGLE PROVIDER SUPPORT**

After comprehensive investigation, Hermes Agent does not implement direct Google/Gemini API provider functionality. All Gemini model access must go through third-party providers like OpenRouter.

---

## Investigation Details

### 1. Provider Architecture Analysis

**Available Providers in Hermes:**
```
1. OpenRouter        2. Nous Portal      3. OpenAI Codex     4. GitHub Copilot ACP
5. GitHub Copilot    6. Anthropic        7. Z.AI/GLM         8. Kimi/Moonshot
9. MiniMax          10. MiniMax China   11. Kilo Code       12. OpenCode Zen
13. OpenCode Go     14. AI Gateway      15. Alibaba Cloud   16. Hugging Face
17. Custom endpoint 18. Cancel
```

**Missing:** No Google/Gemini direct provider option

### 2. Environment Variable Testing

**Test Configuration:**
```bash
GOOGLE_API_KEY=<redacted>  # Valid key was present locally; never commit raw keys.
```

**Status Check:**
```bash
$ docker exec -e GOOGLE_API_KEY=*** hermes hermes status

◆ API Keys
  OpenRouter    ✓ sk-o...e40a
  OpenAI        ✗ (not set)
  Z.AI/GLM      ✗ (not set)
  [... other providers ...]
  # NO GOOGLE API KEY RECOGNITION IN STATUS
```

**Result:** While Hermes recognizes `GOOGLE_API_KEY` in environment blocklists (security), it doesn't register as an active provider.

### 3. Direct Model Access Testing

**Test Command:**
```bash
docker exec -e GOOGLE_API_KEY=*** hermes hermes chat \
  -q "Test Google API" \
  -Q --source operator \
  -m "google/gemini-3.1-flash-lite-preview"
```

**Results:**
```
⚠️  API call failed (attempt 1/3): APIStatusError [HTTP 402]
   🔌 Provider: openrouter  Model: google/gemini-3.1-flash-lite-preview
   🌐 Endpoint: https://openrouter.ai/api/v1
   📝 Error: HTTP 402: insufficient credits (26113 vs 65536 required)
```

**Key Finding:** Even with `GOOGLE_API_KEY` set, Hermes **still routes through OpenRouter provider**, not direct Google API.

---

## Technical Analysis

### Code References Found

**Environment Recognition:**
- `/app/tools/environments/local.py` - Comment: `"Gemini / Google AI Studio"`
- Test files reference `GOOGLE_API_KEY` for validation
- Security blocklists include `GOOGLE_API_KEY`

**Provider Implementation:**
- No Google provider class found in Hermes codebase
- All Gemini models route through third-party providers
- `google/` model prefixes require OpenRouter or compatible provider

### Architecture Implications

1. **Design Pattern:** Hermes uses provider abstraction layer
2. **Current Providers:** 18 provider options, no Google implementation
3. **Model Routing:** Model IDs with `google/` prefix route to compatible providers
4. **API Key Usage:** `GOOGLE_API_KEY` recognized for security, not provider access

---

## Credit Status Update

**Previous Status:** 1,566 tokens available  
**Current Status:** 26,113 tokens available (partial improvement)  
**Required for Hermes:** 65,536 tokens per operation  
**Gap:** Still 39,423 tokens short for testing

**Note:** Credits were partially increased but remain insufficient for Hermes operations.

---

## Alternative Approaches Considered

### Option 1: Custom Endpoint Configuration
- Hermes offers "Custom endpoint" provider (#17)
- Would need Google API OpenAI-compatible wrapper
- Not direct Google API as requested

### Option 2: Anthropic Provider (Working)
- Hermes has native Anthropic provider support  
- Could demonstrate Hermes-native FLOW operations
- Different model than requested

### Option 3: OpenRouter Resolution
- Fund OpenRouter account to 65,536+ tokens
- Use `google/gemini-3.1-flash-lite-preview` through OpenRouter
- Third-party provider, not direct Google API

---

## FINAL VERDICT

**BLOCKED BY HERMES PROVIDER SUPPORT**

### Primary Finding
Hermes Agent **does not support direct Google Gemini API provider configuration**. The architecture requires all Gemini access to go through third-party providers.

### User Requirements vs Reality
- **Requested:** Direct Google API path with provided keys
- **Reality:** Hermes only supports Google models through OpenRouter/other providers
- **Gap:** Architectural limitation, not configuration issue

### Recommendations

1. **Use Alternative Agent** - Select tool with native Google provider support
2. **Modify Hermes Source** - Add Google provider implementation (development effort)
3. **Accept Third-Party Route** - Fund OpenRouter for Gemini access (not direct)
4. **Change Model Target** - Use native Anthropic/other providers for proof

### Technical Resolution Required

To meet the request for direct Google API usage, would need either:
- **Different agent** with Google provider support, OR
- **Hermes codebase modification** to add Google provider, OR  
- **Alternative proof approach** using supported providers

**Current Assessment:** Cannot proceed with requested "direct Google Gemini API path" due to Hermes architecture limitations.

---

## Documentation Status

All investigation documents updated with findings:
- ✅ [HERMES_FINAL_VERDICT.md](./HERMES_FINAL_VERDICT.md)
- ✅ [hermes_operator_runtime_test.md](./state/reports/hermes_operator_runtime_test.md)  
- ✅ [hermes_agent_capability_research.md](./state/reports/hermes_agent_capability_research.md)
- ✅ [hermes_flow_integration_design.md](./state/reports/hermes_flow_integration_design.md)
- ✅ [hermes_operator_security_boundaries.md](./state/reports/hermes_operator_security_boundaries.md)

**Investigation Status:** COMPLETE - Architecture limitation confirmed
