from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from matplotlib.lines import Line2D

import io, base64
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
from matplotlib import ticker


try:
    from screener_adapter import screen_mosfet  
except Exception:
    def screen_mosfet(props, device, conditions):
        metrics = {
            "SS_mVdec": 65.8,
            "Vth_V": 1.093,
            "Ion_A_per_um": 0.0,
            "Ioff_proxy": 3.238e-28,
            "gm_S_per_um": 0.0,
            "ft_Hz": 0.0,
            "r0_ohm_per_um": 0.0,
            "DIBL_mV_per_V": 2.5,
            "Stab_score": 0.646
        }
        percentiles = {
            "SS_percent": 72.8,
            "Vth_score_percent": 63.8,
            "Ion_percent": 25.0,
            "Ioff_percent": 25.0,
            "gm_percent": 25.0,
            "fT_percent": 25.0,
            "r0_percent": 25.0,
            "DIBL_percent": 34.1,
            "Stab_percent": 45.3
        }
        return {
            "metrics": metrics,
            "percentiles": percentiles,
            "score": 0.72,
            "decision": "unsure",
            "uncertainty": 0,
            "model_version": "colab_screener_v1"
        }

# ---------- FastAPI ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScreenReq(BaseModel):
    props: dict
    device: str
    conditions: dict

# ---------- 차트 렌더 ----------
LABELS = {
    "SS_percent": "SS",
    "Vth_score_percent": "Vth score",
    "Ion_percent": "Ion",
    "Ioff_percent": "Ioff",
    "gm_percent": "gm",
    "fT_percent": "fT",
    "r0_percent": "r0",
    "DIBL_percent": "DIBL",
    "Stab_percent": "Stability",
}
PRIORITY = [
    "Ion_percent", "gm_percent", "fT_percent",
    "Vth_score_percent", "SS_percent", "DIBL_percent",
    "r0_percent", "Ioff_percent", "Stab_percent",
]

def make_ranking_chart(percentiles: dict, baseline_pcts: dict | None = None) -> str:
    """
    percentiles(0~100)을 다크테마 가로막대로 렌더 → base64 PNG 반환
    baseline_pcts 가 주어지면, 각 지표별로 베이스라인 재료들의 점과 범례도 함께 그림.
    baseline_pcts 예시:
      {
        "Si":  {"Ion_percent": ..., "gm_percent": ..., ...},
        "GaN": {"Ion_percent": ..., ...},
        ...
      }
    """
    if not percentiles:
        return ""

    baseline_pcts = baseline_pcts or {}

    # 순서 정리
    keys_all = list(percentiles.keys())
    ordered = [k for k in PRIORITY if k in percentiles] + [
        k for k in keys_all if k not in PRIORITY
    ]

    vals = [float(percentiles[k]) for k in ordered]
    labels = [LABELS.get(k, k) for k in ordered]

    # 내림차순 정렬
    order_idx = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)
    vals = [vals[i] for i in order_idx]
    labels = [labels[i] for i in order_idx]
    ordered = [ordered[i] for i in order_idx]

    # 크기 설정
    fig_h = 0.48 * len(vals) + 1.6
    fig, ax = plt.subplots(figsize=(9, fig_h), facecolor="#111111")
    ax.set_facecolor("#111111")

    base = (0.36, 0.62, 0.94)
    colors = [
        (
            base[0] * (0.8 + 0.2 * i / len(vals)),
            base[1] * (0.8 + 0.2 * i / len(vals)),
            base[2] * (0.8 + 0.2 * i / len(vals)),
        )
        for i in range(len(vals))
    ]

    y = range(len(vals))
    bars = ax.barh(list(y), vals, color=colors, edgecolor="#333333", linewidth=0.8)

    # 후보 재료 퍼센트 레이블
    for b, v in zip(bars, vals):
        ax.text(
            b.get_width() + 1.2,
            b.get_y() + b.get_height() / 2,
            f"{v:.1f}%",
            va="center",
            ha="left",
            color="#eaeaea",
            fontsize=11,
        )

    ax.set_yticks(list(y), labels=labels, color="#e0e0e0", fontsize=12)
    ax.set_xlim(0, max(100, max(vals) + 6))
    ax.xaxis.set_major_formatter(ticker.PercentFormatter(xmax=100))
    ax.tick_params(axis="x", colors="#cfcfcf", labelsize=11)
    ax.grid(axis="x", color="#2a2a2a", linestyle="--", linewidth=0.7, alpha=0.8)
    ax.set_xlabel("Percentile", color="#dddddd", labelpad=8)
    ax.set_title(
        "Relative Ranking vs Baselines", color="#ffffff", pad=10, fontsize=16, weight="bold"
    )

    # ---------- 여기부터 baseline 점 + 범례 ----------
    if baseline_pcts:
        cmap = plt.get_cmap("tab20")
        base_names = list(baseline_pcts.keys())

        # 각 지표(ordered[i])의 y 위치에 베이스라인 점 찍기
        for j, name in enumerate(base_names):
            color = cmap(j % 20)
            bp = baseline_pcts[name]
            for i, pkey in enumerate(ordered):
                if pkey in bp:
                    try:
                        x = float(bp[pkey])
                    except Exception:
                        continue
                    ax.plot(x, i, "o", color=color, markersize=4, alpha=0.95)

        # 범례: Ion_percent 기준으로 퍼센트 표시 (없으면 첫 키 사용)
        ref_key = "Ion_percent"
        if not any(ref_key in baseline_pcts[n] for n in base_names):
            # Ion_percent가 없으면 ordered 첫 번째를 사용
            if ordered:
                ref_key = ordered[0]

        legend_handles: list[Line2D] = []
        legend_labels: list[str] = []
        for j, name in enumerate(base_names):
            color = cmap(j % 20)
            h = Line2D([0], [0], marker="o", linestyle="", color=color, markersize=6)
            legend_handles.append(h)
            val = baseline_pcts[name].get(ref_key)
            if isinstance(val, (int, float)):
                legend_labels.append(f"{name} {val:.1f}%")
            else:
                legend_labels.append(str(name))

        if legend_handles:
            ax.legend(
                legend_handles,
                legend_labels,
                title=f"Baseline ({ref_key})",
                bbox_to_anchor=(1.02, 1.0),
                loc="upper left",
                frameon=False,
                fontsize=8,
                title_fontsize=9,
            )

    plt.tight_layout(pad=1.0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# ---------- 엔드포인트 ----------
@app.post("/screen")
def screen(req: ScreenReq):
    temp = float((req.conditions or {}).get("temp", 300.0))
    vdd  = float((req.conditions or {}).get("vdd", 0.9))

    result = screen_mosfet(req.props, temp=temp, vdd=vdd)

    result["chart"] = make_ranking_chart(
        result.get("percentiles", {}),
        result.get("baseline_percentiles", {})
    )
    return result
