from pathlib import Path
from io import StringIO

import base64
from io import StringIO, BytesIO
import torch
from ase.io import read
from alignn.ff.ff import AlignnAtomwiseCalculator

BASE_DIR = Path(__file__).resolve().parent
MODELS_ROOT = BASE_DIR / "models"

MODEL_PATHS = {
    "bandgap": MODELS_ROOT / "bandgap" / "temp(band gap)",
    "formation_energy": MODELS_ROOT / "formation energy" / "temp(formation energy)",
    "permittivity": MODELS_ROOT / "permittivity" / "temp(permittivity)",
}

_CALCS = {}

def _get_calc(name: str):
    if name in _CALCS:
        return _CALCS[name]

    model_dir = MODEL_PATHS[name]
    calc = AlignnAtomwiseCalculator(path=str(model_dir))
    _CALCS[name] = calc
    return calc

def _cif_to_atoms(cif_text: str):
    from io import StringIO
    try:
        atoms = read(StringIO(cif_text), format="cif")
        return atoms
    except Exception as e:
        print("[ERROR] CIF parsing failed:", e)
        raise ValueError("Invalid CIF text format")



def predict_props_from_cif(cif_text: str):
    atoms = _cif_to_atoms(cif_text)

    results = {}

    # 각 모델별 계산 처리
    for prop_name, model_dir in MODEL_PATHS.items():
        calc = _get_calc(prop_name)
        atoms.set_calculator(calc)
        value = atoms.get_potential_energy()
        results[prop_name] = value

    return results



if __name__ == "__main__":
    # backend 폴더 안에 test.cif가 있으면 그걸 읽어서 예측해보고,
    # 없으면 안내만 출력
    cif_path = BASE_DIR / "test.cif"
    if cif_path.exists():
        txt = cif_path.read_text()
        props = predict_props_from_cif(txt)
        print(props)
    else:
        print("backend 폴더에 test.cif 파일이 없어서, 예측을 실행하지 않았어요.")
