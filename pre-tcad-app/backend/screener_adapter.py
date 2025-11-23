from typing import Dict, Any
import m_screener as M 

def screen_mosfet(props: Dict[str, float], *, temp: float = 300.0, vdd: float = 0.9) -> Dict[str, Any]:
    """
    props 예시 키:
      Eg_eV, eps_r, Ef_eV_atom, mu_cm2_Vs, tox_nm, eps_ox, NA_cm3, L_nm, W_um
    """
    # 1) 재료 물성
    try:
        m = M.MaterialInputs(
            Eg_eV=float(props["Eg_eV"]),
            eps_r=float(props["eps_r"]),
            Ef_eV_atom=float(props["Ef_eV_atom"]),
        )
    except KeyError as e:
        raise KeyError(f"필수 키 누락: {e}. 필요한 키: Eg_eV, eps_r, Ef_eV_atom")

    # 2) 공정/설계 파라미터
    s = M.SliderParams(
        tox_nm=float(props.get("tox_nm", M.SliderParams.tox_nm)),
        eps_ox=float(props.get("eps_ox", M.SliderParams.eps_ox)),
        NA_cm3=float(props.get("NA_cm3", M.SliderParams.NA_cm3)),
        L_nm=float(props.get("L_nm", M.SliderParams.L_nm)),
        VDD_V=float(props.get("VDD_V", vdd)),
        T_K=float(props.get("T_K", temp)),
        W_um=float(props.get("W_um", M.SliderParams.W_um)),
        mu_cm2_Vs=float(props.get("mu_cm2_Vs", M.SliderParams.mu_cm2_Vs)),
    )

    # 3) 지표 계산 및 백분위(후보 재료)
    metrics = M.compute_metrics(m, s)
    perc    = M.compute_percentiles(metrics)

    # 3-1) 베이스라인 재료들의 퍼센트도 같이 계산 (점/범례용)
    baseline_percentiles: Dict[str, Dict[str, float]] = {}
    try:
        for name, Eg, eps_r_b, Ef in M.BASELINE:
            bm = M.MaterialInputs(Eg_eV=Eg, eps_r=eps_r_b, Ef_eV_atom=Ef)
            bm_metrics = M.compute_metrics(bm, s)
            bm_perc    = M.compute_percentiles(bm_metrics)
            baseline_percentiles[name] = bm_perc
    except Exception:
        # 문제가 생겨도 메인 로직은 돌아가도록
        baseline_percentiles = {}

    # 4) 종합 점수/판단 (간단 가중합 예시)
    score = float(
        0.25 * perc.get("Ion_percent", 0.0)
        + 0.25 * perc.get("gm_percent", 0.0)
        + 0.25 * perc.get("fT_percent", 0.0)
        + 0.25 * perc.get("Vth_score_percent", 0.0)
    )
    decision = "suitable" if score >= 70 else ("unsure" if score >= 50 else "unsuitable")

    result = {
        "metrics": {
            "SS_mVdec":      metrics.get("SS_mVdec"),
            "Vth_V":         metrics.get("Vth_V"),
            "Ion_A_per_um":  metrics.get("Ion_A_per_um"),
            "gm_S_per_um":   metrics.get("gm_S_per_um"),
            "ft_Hz":         metrics.get("ft_Hz"),
            "r0_ohm_per_um": metrics.get("r0_ohm_per_um"),
            "DIBL_mV_per_V": metrics.get("DIBL_mV_per_V"),
            "Stab_score":    metrics.get("Stab_score"),
            "Ioff_proxy":    metrics.get("Ioff_proxy"),
        },
        "percentiles": perc,
        "baseline_percentiles": baseline_percentiles,  # 👈 점/범례용
        "score": score,
        "decision": decision,
        "uncertainty": 0.0,
        "explain": [],
        "model_version": "colab_screener_v1",
    }
    return result
