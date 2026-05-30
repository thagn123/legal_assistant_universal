# Release Gate Report — LexAI / ULKA

**Generated:** 2026-05-30T02:28:41.439211+00:00

## Verdict

| Gate | Result |
|---|---|
| Beta release | ✅ PASS_BETA |
| GA release | ❌ FAIL_GA |

## Hard Gates (zero tolerance)

| Gate | Status | Reason |
|---|---|---|
| HG-1: P0 contradictions = 0 | ✅ | clean |
| HG-2: Forbidden phrases = 0 | ✅ | clean |
| HG-3: API 500 errors = 0 | ✅ | clean |
| HG-4: Demo labelling correct | ✅ | clean |
| HG-5: Cross-domain error = 0% | ✅ | clean |
| HG-6: Score threshold leak = 0 | ✅ | clean |

## GA Gate Failures

- ❌ Benchmark gate fail: fallback_demo_rate_pct: 100.0 > 30.0 (target)
- ❌ Manual QA: 14/15 pass — need 15/15 for GA

## Conclusion

Beta gate passed — system can be deployed to beta users.
GA gate not yet passed — resolve GA failures before full release.