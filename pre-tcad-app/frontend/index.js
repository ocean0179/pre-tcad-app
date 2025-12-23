// =========================
//  공통 유틸
// =========================
const $ = id => document.getElementById(id);
const API = "https://pre-tcad-app.onrender.com";   // FastAPI 서버 주소

function toNum(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const v = el.value.trim();
    return v === "" ? null : Number(v);
}

function setVals(obj) {
    for (const [k, v] of Object.entries(obj)) {
        const el = $(k);
        if (el) el.value = v;
    }
}



// =========================
//  프리셋
// =========================
const PRESETS = {
    si: {
        Eg_eV: 1.12, eps_r: 11.7, Ef_eV_atom: -1.0, mu_cm2_Vs: 450,
        tox_nm: 1.2, eps_ox: 3.9, NA_cm3: 1e17,
        L_nm: 45, W_um: 1.0,
        T: 300, VDD: 1.0
    },

    si_long: {
        Eg_eV: 1.12, eps_r: 11.7, Ef_eV_atom: -1.0, mu_cm2_Vs: 1350,
        tox_nm: 2.0, eps_ox: 3.9, NA_cm3: 1e16,
        L_nm: 180, W_um: 1.0,
        T: 300, VDD: 1.8
    },

    short: {
        Eg_eV: 1.12, eps_r: 11.7, Ef_eV_atom: -1.0, mu_cm2_Vs: 300,
        tox_nm: 1.0, eps_ox: 3.9, NA_cm3: 5e17,
        L_nm: 20, W_um: 1.0,
        T: 300, VDD: 0.7
    }
};

document.querySelectorAll(".preset").forEach(btn => {
    btn.addEventListener("click", () => {
        const p = PRESETS[btn.dataset.preset];
        setVals(p);
    });
});



// =========================
//  CIF 업로드 → /screen_alignn
// =========================
$("run_cif").onclick = async () => {
    const statusEl = $("cif_status");
    const file = $("cif").files[0];

    if (!file) {
        statusEl.textContent = "먼저 CIF 파일을 선택해주세요.";
        return;
    }

    statusEl.textContent = "ALIGNN 예측 + MOSFET 계산 중...";

    try {
        const cifText = await file.text();

        const payload = {
            cif: cifText,
            device: "nmos",
            conditions: { temp: 300, vdd: 0.9 }
        };

        const res = await fetch(`${API}/screen_alignn`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            let msg;
            try { msg = JSON.stringify(await res.json()); }
            catch { msg = await res.text(); }
            throw new Error("status " + res.status + " / " + msg);
        }

        const data = await res.json();

        // 저장
        localStorage.setItem("screener_result", JSON.stringify(data));
        localStorage.setItem("screener_input", JSON.stringify({
            via: "cif",
            cif_filename: file.name
        }));

        statusEl.textContent = "계산 완료! 결과 페이지로 이동합니다...";

        // 이동
        const base = window.location.pathname.replace(/index\.html?$/, "");
        window.location.href = base + "result.html";

    } catch (e) {
        console.error(e);
        statusEl.textContent = "오류: " + e.message;
        alert("오류: " + e.message);
    }
};



// =========================
//  수동 입력 → /screen
// =========================
$("run").onclick = async () => {
    const statusEl = $("status");
    statusEl.textContent = "서버 계산 중...";

    const payload = {
        props: {
            Eg_eV: toNum("Eg_e_V"),     // ❗ 오타 없도록 확인
            Eg_eV: toNum("Eg_eV"),
            eps_r: toNum("eps_r"),
            Ef_eV_atom: toNum("Ef_eV_atom"),
            mu_cm2_Vs: toNum("mu_cm2_Vs"),

            tox_nm: toNum("tox_nm"),
            eps_ox: toNum("eps_ox"),
            NA_cm3: toNum("NA_cm3"),
            L_nm: toNum("L_nm"),
            W_um: toNum("W_um")
        },

        device: "nmos",

        conditions: {
            temp: toNum("T"),
            vdd: toNum("VDD")
        }
    };

    try {
        const res = await fetch(`${API}/screen`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            let msg;
            try { msg = JSON.stringify(await res.json()); }
            catch { msg = await res.text(); }
            throw new Error(`status ${res.status} / ${msg}`);
        }

        const data = await res.json();

        // 저장
        localStorage.setItem("screener_input", JSON.stringify(payload));
        localStorage.setItem("screener_result", JSON.stringify(data));

        statusEl.textContent = "계산 완료! 결과 페이지로 이동합니다.";

        // 이동
        const base = window.location.pathname.replace(/index\.html?$/, "");
        window.location.href = base + "result.html";

    } catch (e) {
        console.error(e);
        statusEl.textContent = "오류: " + e.message;
        alert("서버 오류: " + e.message);
    }
};

