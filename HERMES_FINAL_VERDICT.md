# FINAL VERDICT: Hermes Token Interpretation and Provider Path

**Assessment Date:** May 4, 2026  
**System:** FLOW Agent AS Phase 4/5  
**Component:** Hermes Agent Standalone Integration  
**Assessment Scope:** Correct token interpretation before further operator-proof work

---

## VERDICT

**MISINTERPRETED TOKEN REQUIREMENT**

`65536` is not a standing dollar balance requirement and it is not proof that Hermes needs "$65 of credits" to operate. In the captured failures, Hermes did **not** explicitly send `max_tokens` or `max_output_tokens`, but OpenRouter still rejected the request as if the request budget were `65536` tokens.

The moving `1566` and `26113` values are therefore best interpreted as **OpenRouter affordability/quota estimates for the selected request path**, not as a Hermes runtime minimum.

---

## Exact Findings

### 1. Exact failing OpenRouter error

**Original failure session:** `20260505_044001_054ad9`  
**HTTP status:** `402`  
**Provider:** `openrouter`  
**Endpoint:** `https://openrouter.ai/api/v1/chat/completions`  
**Model:** `anthropic/claude-opus-4.6`

**Captured response body:**
```json
{
  "message": "This request requires more credits, or fewer max_tokens. You requested up to 65536 tokens, but can only afford 1566. To increase, visit https://openrouter.ai/settings/credits and upgrade to a paid account",
  "code": 402,
  "metadata": {
    "provider_name": null
  }
}
```

**Later failure session:** `20260505_053302_9add25`  
**HTTP status:** `402`  
**Provider:** `openrouter`  
**Endpoint:** `https://openrouter.ai/api/v1/chat/completions`  
**Model:** `google/gemini-3.1-flash-lite-preview`

**Captured response body:**
```json
{
  "message": "This request requires more credits, or fewer max_tokens. You requested up to 65536 tokens, but can only afford 26113. To increase, visit https://openrouter.ai/settings/credits and upgrade to a paid account",
  "code": 402,
  "metadata": {
    "provider_name": null
  }
}
```

### 2. What Hermes actually sent

For both captured failures, the persisted Hermes request dump showed:

- `max_tokens: null`
- `max_output_tokens: null`
- `base_url: https://openrouter.ai/api/v1`

That means Hermes did **not** explicitly request `65536` in the recorded JSON payload. The `65536` value is being applied downstream by the provider path or its default affordability check.

### 3. What the moving `1566` number means

The value changed from `1566` to `26113` between otherwise similar failures. Because it moved while Hermes itself did not change its token fields, the number is not a fixed Hermes context requirement.

Most likely interpretation:

1. **Provider balance / quota translation**: OpenRouter is estimating how many tokens the account can currently fund for that request path.
2. **Not model context availability**: model context windows do not normally jump from `1566` to `26113` based on account state.
3. **Not Hermes preflight only**: the values come from the OpenRouter HTTP 402 response body.
4. **Not a hard Hermes minimum**: Hermes can run successfully on cheaper models.

### 4. Exact model and provider usage

**Default failing path proven by runtime config:**
- `hermes config` reported `Model: anthropic/claude-opus-4.6`
- `hermes status` reported `Provider: OpenRouter`

**Explicit Gemini test path proven by session dump:**
- Model: `google/gemini-3.1-flash-lite-preview`
- Provider path: `openrouter`
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`

**Successful low-cost path:**
- Minimal query session: `20260505_053937_990c73`
- Small FLOW-state query session: `20260505_054042_304ba9`
- Model: `openai/gpt-4.1-nano`
- Base URL: `https://openrouter.ai/api/v1`

### 5. Minimal query result

This minimal Hermes query succeeded on a lower-cost model:

```bash
docker exec hermes hermes chat -q "Reply with exactly: Hermes model path works." -Q --source operator --provider openrouter -m openai/gpt-4.1-nano
```

**Result:**
```text
Hermes model path works.
```

This proves Hermes does **not** require a `$65` balance or a `65536`-token-funded account to operate at all.

### 6. Small FLOW-state smoke test

After correcting model selection, Hermes also completed a limited FLOW-state query:

```bash
docker exec hermes hermes chat -q "List the entries in /hermes/flow/reviews and say whether the directory is empty." -Q --source operator --provider openrouter -m openai/gpt-4.1-nano
```

**Result:**
```text
The directory /hermes/flow/reviews does not appear to contain any entries; it is empty.
```

This was a small operator-style action only. Full operator-proof work remains paused until provider-path conclusions are settled.

---

## Config Inspection Summary

### Effective runtime config observed

- `model`: `anthropic/claude-opus-4.6` by default from `hermes config`
- `provider`: `OpenRouter` from `hermes status`
- `base_url`: `https://openrouter.ai/api/v1` from session metadata
- `context_length`: no explicit user-configured value found in runtime config or request dumps
- `max_tokens`: not explicitly set in captured failing requests
- `max_output_tokens`: not explicitly set in captured failing requests
- `OPENROUTER_API_KEY`: set
- `GEMINI_API_KEY`: not set in runtime env
- `GOOGLE_API_KEY`: not set in runtime env; injecting it did not change the provider path

### Model override findings

The compose file sets `HERMES_DEFAULT_MODEL`, but the live Hermes runtime still reported `anthropic/claude-opus-4.6`. In the current image, the compose-side default-model env setting is not the effective source of truth for the CLI default used in these tests.

---

## Direct Google Path Status

The current Hermes image did not use a direct Google provider path during testing.

Evidence:

1. `hermes chat --help` provider list does not expose a `google` provider.
2. Hermes auth/config code in this image clearly wires `OPENROUTER_API_KEY` into provider auto-selection.
3. Injecting `GOOGLE_API_KEY` still produced a request dump targeting `https://openrouter.ai/api/v1/chat/completions`.

For the requested direct Gemini path, the current runtime remains:

**BLOCKED BY HERMES PROVIDER SUPPORT**

But that is separate from the token-interpretation correction above.

---

## Corrected Conclusion

The previous claim that Hermes "requires 65,536 tokens of credits" was incorrect.

The validated interpretation is:

1. `65536` is the request cap being used by the provider path when `max_tokens` is not explicitly constrained.
2. `1566` and `26113` are OpenRouter affordability/quota numbers for that request path.
3. Hermes itself can operate on cheaper models with the existing account.
4. The immediate practical blockers are model/provider selection and, for the requested direct Gemini route, current Hermes provider support.