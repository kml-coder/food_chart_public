#!/usr/bin/env python3
"""
eval_baselines.py — 학습 없는 베이스라인들을 홀드아웃 test에서 평가한다.

왜 필요한가:
  "DeBERTa MAE 55.19g"만 있으면 "55g이 좋은 겁니까?"에 답할 수 없다.
  비교 대상이 있어야 모델이 기여한 몫이 드러난다.
  특히 이 데이터는 {unit, size, name} → gram 이라서
  "unit별 평균만 내도 되는 거 아니냐"는 의심이 자연스럽다. 그걸 직접 반박한다.

무엇을 재나:
  1) 베이스라인 5종 (전역평균/전역중앙값/unit평균/unit중앙값/unit×size중앙값)
     + server.py에 하드코딩된 heuristic 딕셔너리
  2) 같은 unit 안에서 재료별 그램이 얼마나 흩어지는지 (= unit 룩업의 상한)
  3) 파이차트 조각 비율 오차 시뮬레이션 (원 데이터에 recipe id가 없어 합성)

의존성: numpy 만. (torch/sklearn 불필요)
실행:  python3 eval_baselines.py
출력:  artifacts/baseline_metrics.md  +  stdout
"""

import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "final_unit_removed.json")          # v3 (USDA 보강본)
# artifacts/ 는 .gitignore 대상(대용량 가중치 보관용)이라 결과는 docs/ 로 쓴다 — 레포에 남아야 함.
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "docs"))
OUT_MD = os.path.join(OUT_DIR, "baseline_metrics.md")

SEED = 42

# ★docs/readme_model_details.md 의 DeBERTa 실험과 **동일한 프로토콜**로 맞춘다.
#   그래야 "DeBERTa MAE 38.87 vs 베이스라인 X"가 같은 저울 위의 비교가 된다.
#     - 필터: gram > 0 만 (상·하한 절단 없음)  → usable 25,983
#     - 분할: train_test_split(test_size=0.2, random_state=42)  → val 5,197
#   sklearn의 ShuffleSplit은 RandomState(seed).permutation(n)을 만들고
#   앞 n_test개를 test로 쓴다. 아래 docs_split()이 그 동작을 그대로 재현한다.
#   (sklearn 미설치 환경에서도 돌게 numpy로만 구현)
DOCS_TEST_FRAC = 0.2


# ── 데이터 ────────────────────────────────────────────────────────────────────

def norm(x):
    return re.sub(r"\s+", " ", str(x or "").strip().lower())


def load_rows():
    with open(DATA) as f:
        raw = json.load(f)
    rows = []
    for r in raw:
        try:
            g = float(r.get("gram"))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(g) or g <= 0:      # docs와 동일 필터: gram > 0
            continue
        rows.append({
            "unit": norm(r.get("unit")),
            "size": norm(r.get("size")),
            "name": norm(r.get("name")),
            "gram": g,
        })
    return rows


def docs_split(rows):
    """sklearn.train_test_split(test_size=0.2, random_state=42)와 동일한 분할을 재현.

    sklearn ShuffleSplit._iter_indices:
        rng = RandomState(42); perm = rng.permutation(n)
        test = perm[:n_test]; train = perm[n_test:n_test+n_train]
    DeBERTa 실험이 이 분할을 썼으므로, 베이스라인도 같은 val에서 재야 비교가 성립한다."""
    n = len(rows)
    n_test = int(np.ceil(n * DOCS_TEST_FRAC))
    n_train = n - n_test
    perm = np.random.RandomState(SEED).permutation(n)
    val = [rows[i] for i in perm[:n_test]]
    train = [rows[i] for i in perm[n_test:n_test + n_train]]
    return train, val


# ── 지표 ──────────────────────────────────────────────────────────────────────

def metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = np.abs(y_pred - y_true)

    mae = float(err.mean())
    medae = float(np.median(err))                       # 중앙값 절대오차 — 정의가 명확
    cut = np.percentile(err, 95)                        # 상위 5% 절단
    robust_mae = float(err[err <= cut].mean())
    mape = float((err / y_true).mean() * 100)
    within20 = float((err / y_true <= 0.20).mean())
    return {
        "MAE": mae,
        "MedAE": medae,
        "RobustMAE": robust_mae,
        "MAPE": mape,
        "Within20": within20,
    }


# ── 베이스라인들 (전부 train에서만 학습, test에서 평가) ────────────────────────

def fit_lookup(train, keyfn, agg):
    table = defaultdict(list)
    for r in train:
        table[keyfn(r)].append(r["gram"])
    return {k: float(agg(v)) for k, v in table.items()}


def predict_lookup(test, table, keyfn, fallback):
    return [table.get(keyfn(r), fallback) for r in test]


# server.py:324 estimate_grams_with_heuristic 의 딕셔너리를 그대로 옮김.
HEURISTIC_UNITS = {
    "cup": 240.0, "cups": 240.0,
    "tablespoon": 15.0, "tablespoons": 15.0, "tbsp": 15.0,
    "teaspoon": 5.0, "teaspoons": 5.0, "tsp": 5.0,
    "ounce": 28.35, "ounces": 28.35, "oz": 28.35,
    "pound": 453.6, "lb": 453.6, "lbs": 453.6,
    "clove": 5.0, "cloves": 5.0,
    "slice": 25.0, "slices": 25.0,
}


def predict_heuristic(test):
    out = []
    for r in test:
        u, n = r["unit"], r["name"]
        if u in HEURISTIC_UNITS:
            out.append(HEURISTIC_UNITS[u])
        elif "egg" in n:
            out.append(50.0)
        elif "onion" in n:
            out.append(110.0)
        elif "garlic" in n:
            out.append(5.0)
        else:
            out.append(30.0)
    return out


# ── 분석 1: 같은 unit 안에서 재료별 그램이 얼마나 흩어지나 ────────────────────

def unit_spread(rows, min_names=8, min_rows=40, top=14):
    """unit 룩업의 이론적 상한을 보여준다.

    같은 'bunch'여도 파슬리 한 단과 파 한 단은 무게가 다르다.
    unit만 보는 룩업은 이 분산을 원리적으로 설명할 수 없다 —
    아무리 잘 맞춰도 unit 안 분산이 그대로 오차로 남는다."""
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[r["unit"]].append(r)

    out = []
    for u, rs in by_unit.items():
        if len(rs) < min_rows:
            continue
        by_name = defaultdict(list)
        for r in rs:
            by_name[r["name"]].append(r["gram"])
        if len(by_name) < min_names:
            continue
        name_medians = np.array([np.median(v) for v in by_name.values()])
        grams = np.array([r["gram"] for r in rs])

        # unit 평균으로 예측했을 때 남는 오차(= 이 unit에서 룩업의 한계)
        resid = float(np.abs(grams - grams.mean()).mean())
        out.append({
            "unit": u or "(없음)",
            "rows": len(rs),
            "names": len(by_name),
            "median": float(np.median(grams)),
            "p10": float(np.percentile(name_medians, 10)),
            "p90": float(np.percentile(name_medians, 90)),
            "ratio": float(np.percentile(name_medians, 90) / max(np.percentile(name_medians, 10), 1e-9)),
            "lookup_mae": resid,
        })
    out.sort(key=lambda d: -d["rows"])
    return out[:top]


def named_examples(rows, unit, names):
    """특정 unit에서 재료별 중앙값을 뽑아 예시로 보여준다."""
    by_name = defaultdict(list)
    for r in rows:
        if r["unit"] == unit:
            by_name[r["name"]].append(r["gram"])
    hits = []
    for want in names:
        for n, v in by_name.items():
            if want in n and len(v) >= 2:
                hits.append((n, float(np.median(v)), len(v)))
                break
    return hits


# ── 분석 2: 파이차트 조각 비율 오차 시뮬레이션 ────────────────────────────────

def chart_slice_error(test, preds, n_recipes=4000, k=10, seed=7):
    """★가정을 명시한다:
       원 데이터에 recipe id가 없다(README에도 기재됨). 그래서 실제 레시피 단위로는
       측정할 수 없고, test 행을 k개씩 무작위로 묶어 '합성 레시피'를 만든다.
       실제 레시피는 무작위 조합이 아니므로 이 수치는 근사다.

       재는 것: 각 재료가 파이차트에서 차지하는 비율(%)의 오차(%p).
       그램 오차가 아니라 '보이는 크기'의 오차다."""
    y = np.asarray([r["gram"] for r in test], dtype=float)
    p = np.asarray(preds, dtype=float)
    rng = np.random.default_rng(seed)

    slice_errs, max_errs, true_shares = [], [], []
    for _ in range(n_recipes):
        idx = rng.choice(len(y), size=k, replace=False)
        ty, tp = y[idx], p[idx]
        if ty.sum() <= 0 or tp.sum() <= 0:
            continue
        share_true = ty / ty.sum() * 100
        share_pred = tp / tp.sum() * 100
        e = np.abs(share_pred - share_true)
        slice_errs.append(e)
        max_errs.append(e.max())
        true_shares.append(share_true)

    slice_errs = np.concatenate(slice_errs)
    true_shares = np.concatenate(true_shares)

    # 큰 재료 / 작은 재료로 갈라서 본다 — 주장의 핵심
    big = true_shares >= 20.0
    small = true_shares < 2.0
    return {
        "mean_slice_err_pp": float(slice_errs.mean()),
        "median_slice_err_pp": float(np.median(slice_errs)),
        "p90_slice_err_pp": float(np.percentile(slice_errs, 90)),
        "mean_max_slice_err_pp": float(np.mean(max_errs)),
        "big_slice_err_pp": float(slice_errs[big].mean()) if big.any() else float("nan"),
        "small_slice_err_pp": float(slice_errs[small].mean()) if small.any() else float("nan"),
        "n_big": int(big.sum()),
        "n_small": int(small.sum()),
    }


# ── 실행 ──────────────────────────────────────────────────────────────────────

def main():
    rows = load_rows()
    train, test = docs_split(rows)      # test = DeBERTa 실험의 validation set과 동일

    lines = []
    def emit(s=""):
        print(s)
        lines.append(s)

    emit("# 베이스라인 평가")
    emit()
    emit(f"- 데이터: `final_unit_removed.json` (v3, USDA 보강본)")
    emit(f"- 유효 행 (gram > 0): **{len(rows):,}**")
    emit(f"- 분할: train **{len(train):,}** / validation **{len(test):,}**")
    emit(f"  — `train_test_split(test_size=0.2, random_state={SEED})` 재현")
    emit(f"- **`docs/readme_model_details.md`의 DeBERTa 실험과 동일한 분할.** 같은 저울 위의 비교다.")
    emit(f"- 모든 베이스라인은 **train에서만** 통계를 뽑고 **validation**에서 평가")
    emit()
    emit("> `RobustMAE` = 절대오차 상위 5% 제외 평균. `MedAE` = 절대오차 중앙값(정의가 모호하지 않음).")
    emit()

    gmean = float(np.mean([r["gram"] for r in train]))
    gmed = float(np.median([r["gram"] for r in train]))

    unit_mean = fit_lookup(train, lambda r: r["unit"], np.mean)
    unit_med = fit_lookup(train, lambda r: r["unit"], np.median)
    us_med = fit_lookup(train, lambda r: (r["unit"], r["size"]), np.median)

    y_test = [r["gram"] for r in test]

    candidates = [
        ("전역 평균", [gmean] * len(test)),
        ("전역 중앙값", [gmed] * len(test)),
        ("server.py heuristic 딕셔너리", predict_heuristic(test)),
        ("unit 평균 룩업", predict_lookup(test, unit_mean, lambda r: r["unit"], gmean)),
        ("unit 중앙값 룩업", predict_lookup(test, unit_med, lambda r: r["unit"], gmed)),
        ("unit×size 중앙값 룩업", predict_lookup(test, us_med, lambda r: (r["unit"], r["size"]), gmed)),
    ]

    emit("## 1. 베이스라인 vs 학습 모델 (동일 validation set)")
    emit()
    emit("| 방식 | 학습 | MAE (g) | MedAE (g) | RobustMAE (g) | MAPE (%) | Within 20% |")
    emit("|---|:--:|---:|---:|---:|---:|---:|")
    results = {}
    for label, pred in candidates:
        m = metrics(y_test, pred)
        results[label] = (m, pred)
        emit(f"| {label} | ✗ | {m['MAE']:.2f} | {m['MedAE']:.2f} | {m['RobustMAE']:.2f} "
             f"| {m['MAPE']:.1f} | {m['Within20']:.4f} |")
    emit(f"| **DeBERTa v3 (채택)** | ✓ | **38.87** | — | — | **40.5** | **0.5440** |")
    emit()
    emit("> DeBERTa 행 출처: `docs/readme_model_details.md`. 같은 데이터·같은 분할 프로토콜이다.")
    emit("> (⚠️ 루트의 `readme_model_details_ko.md`에는 다른 수치(MAE 55.19 / MAPE 176%)가 있는데,")
    emit(">  그건 이전 데이터셋 버전의 실험이다. 문서 하나로 정리할 것.)")
    emit()

    best_lookup = min(
        (l for l in results if "룩업" in l or "heuristic" in l),
        key=lambda l: results[l][0]["MAE"],
    )
    bm = results[best_lookup][0]
    emit(f"**가장 좋은 무학습 베이스라인: {best_lookup} — MAE {bm['MAE']:.2f} g / Within20 {bm['Within20']:.3f}**")
    emit()
    emit(f"| 비교 | 무학습 최고 | DeBERTa | 개선 |")
    emit(f"|---|---:|---:|---:|")
    emit(f"| MAE (g) | {bm['MAE']:.2f} | 38.87 | **−{(1 - 38.87 / bm['MAE']) * 100:.0f}%** |")
    emit(f"| MAPE (%) | {bm['MAPE']:.1f} | 40.5 | **−{(1 - 40.5 / bm['MAPE']) * 100:.0f}%** |")
    emit(f"| Within 20% | {bm['Within20']:.3f} | 0.544 | **{0.544 / bm['Within20']:.2f}배** |")
    emit()

    # ── 2. unit 안 분산 ──
    emit("## 2. 왜 unit 룩업으로는 부족한가")
    emit()
    emit("같은 unit이어도 재료가 다르면 그램이 다르다. unit만 보는 룩업은 이 분산을")
    emit("**원리적으로 설명할 수 없다** — 아무리 잘 맞춰도 unit 안 분산이 그대로 오차로 남는다.")
    emit()
    emit("| unit | 행 수 | 재료 종류 | 중앙값(g) | 재료별 중앙값 p10 | p90 | p90/p10 | 룩업 한계 MAE(g) |")
    emit("|---|---:|---:|---:|---:|---:|---:|---:|")
    for d in unit_spread(train):
        emit(f"| `{d['unit']}` | {d['rows']:,} | {d['names']:,} | {d['median']:.1f} "
             f"| {d['p10']:.1f} | {d['p90']:.1f} | **{d['ratio']:.1f}×** | {d['lookup_mae']:.1f} |")
    emit()

    for u in ("bunch", "handful", "sprig", "cup", "clove", "stalk"):
        ex = named_examples(train, u, ["parsley", "cilantro", "coriander", "green onion",
                                        "scallion", "spinach", "basil", "kale", "flour",
                                        "sugar", "milk", "garlic", "celery"])
        if len(ex) >= 3:
            emit(f"**`{u}` 예시 (재료별 중앙값):** " +
                 " · ".join(f"{n} {g:.0f}g" for n, g, _ in ex[:6]))
    emit()

    # ── 3. 차트 조각 오차 ──
    emit("## 3. 파이차트 조각 비율 오차")
    emit()
    emit("그램 오차가 아니라 **차트에서 보이는 크기의 오차(%p)** 를 잰다.")
    emit()
    emit("> **가정:** 원 데이터에 recipe id가 없다(README에 기재됨). 실제 레시피 단위로는")
    emit("> 잴 수 없어서, test 행을 무작위 k개씩 묶어 **합성 레시피**를 만들었다.")
    emit("> 실제 레시피는 무작위 조합이 아니므로 근사값이다.")
    emit()
    emit("| 베이스라인 | k | 조각오차 평균(%p) | 중앙값 | p90 | 레시피당 최대 평균 | 큰 조각(≥20%) | 작은 조각(<2%) |")
    emit("|---|---:|---:|---:|---:|---:|---:|---:|")
    seen = set()
    for label in [best_lookup, "unit 중앙값 룩업", "server.py heuristic 딕셔너리", "전역 중앙값"]:
        if label not in results or label in seen:
            continue
        seen.add(label)
        pred = results[label][1]
        for k in (10,):
            c = chart_slice_error(test, pred, k=k)
            emit(f"| {label} | {k} | **{c['mean_slice_err_pp']:.2f}** | {c['median_slice_err_pp']:.2f} "
                 f"| {c['p90_slice_err_pp']:.2f} | {c['mean_max_slice_err_pp']:.2f} "
                 f"| {c['big_slice_err_pp']:.2f} | {c['small_slice_err_pp']:.2f} |")
    emit()
    c = chart_slice_error(test, results[best_lookup][1], k=10)
    emit(f"**핵심:** 작은 조각(<2%)의 평균 오차는 **{c['small_slice_err_pp']:.2f}%p** — 눈으로 구별 불가능하다.")
    emit(f"큰 조각(≥20%)은 **{c['big_slice_err_pp']:.2f}%p**로 훨씬 크다.")
    emit("즉 **차트 정확도는 큰 재료가 결정하고, 소량 재료의 MAPE 폭발은 시각적으로 무의미하다.**")
    emit()

    # ── 4. MAPE가 왜 터지나 ──
    emit("## 4. MAPE는 왜 이 문제에 안 맞나")
    emit()
    pred = results[best_lookup][1]
    y = np.asarray(y_test, dtype=float)
    p = np.asarray(pred, dtype=float)
    ape = np.abs(p - y) / y * 100
    aerr = np.abs(p - y)
    emit(f"`{best_lookup}` 기준, 정답 그램 구간별 오차:")
    emit()
    emit("| 정답 구간 | 행 수 | 절대오차 평균(g) | MAPE(%) |")
    emit("|---|---:|---:|---:|")
    for lo, hi, lab in [(0, 5, "0–5 g"), (5, 20, "5–20 g"), (20, 100, "20–100 g"),
                        (100, 300, "100–300 g"), (300, 1e9, "300 g+")]:
        m = (y >= lo) & (y < hi)
        if m.sum() == 0:
            continue
        emit(f"| {lab} | {int(m.sum()):,} | {aerr[m].mean():.1f} | **{ape[m].mean():.0f}** |")
    emit()
    emit("**절대오차는 큰 재료에서 크고, MAPE는 작은 재료에서 폭발한다.**")
    emit("두 지표가 정반대를 가리킨다 — 그래서 MAPE 단독으로는 이 문제를 설명할 수 없다.")
    emit()

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n→ 저장: {OUT_MD}", file=sys.stderr)


if __name__ == "__main__":
    main()
