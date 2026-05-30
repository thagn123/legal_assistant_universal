# Retrieval Benchmark Report — LexAI / ULKA

**Generated:** 2026-05-30T02:03:25.303506+00:00
**Mode:** http (testclient = no real MongoDB)
**Gate:** ❌ FAIL

## Metrics vs Targets

| Metric | Value | Target | Status |
|---|---|---|---|
| top-1 domain accuracy | 96.6% | ≥85% | ✅ |
| top-3 domain accuracy | 96.6% | ≥90% | ✅ |
| cross-domain error | 0.0% | 0% | ✅ |
| empty rate | 0.0% | 0% | ✅ |
| fallback/demo rate | 100.0% | ≤30% | ❌ |
| avg top-1 score | 0.5247 | ≥0.55 | ❌ |

## Gate Failures

- ❌ fallback_demo_rate_pct: 100.0 > 30.0 (target)

## Per-query Results

| ID | Expected | Top-1 | Score | T1✓ | T3✓ | Fallback | Demo | Empty | XDomain |
|---|---|---|---|---|---|---|---|---|---|
| Q01 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q02 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q03 | dat_dai | hanh_chinh | 0.50 | ❌ | ❌ | Y | Y |  |  |
| Q04 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q05 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q06 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q07 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q08 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q09 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q10 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q11 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q12 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q13 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q14 | hop_dong | hop_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q15 | gia_dinh | gia_dinh | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q16 | gia_dinh | gia_dinh | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q17 | gia_dinh | gia_dinh | 0.87 | ✅ | ✅ | Y | Y |  |  |
| Q18 | dan_su | dan_su | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q19 | dan_su | dan_su | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q20 | hop_dong | hop_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q21 | hop_dong | hop_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q22 | hop_dong | hop_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q23 | hop_dong | hop_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q24 | hanh_chinh | hanh_chinh | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q25 | hanh_chinh | hanh_chinh | 0.50 | ✅ | ✅ | Y | Y |  |  |
| Q26 | dat_dai | dat_dai | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q27 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |
| Q28 | general | hop_dong | 0.50 | ❌ | ❌ | Y |  |  |  |
| Q29 | lao_dong | lao_dong | 0.87 | ✅ | ✅ | Y | Y |  |  |
| Q30 | lao_dong | lao_dong | 0.50 | ✅ | ✅ | Y |  |  |  |

## Worst 5 Queries by Score

| ID | Score | Fallback |
|---|---|---|
| Q01 | 0.500 | Y |
| Q02 | 0.500 | Y |
| Q03 | 0.500 | Y |
| Q04 | 0.500 | Y |
| Q05 | 0.500 | Y |