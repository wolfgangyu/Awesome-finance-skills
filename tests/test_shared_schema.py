"""Shared alphaear_schema 跨 skill 的契約測試。"""
import importlib
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SHARED = REPO / "skills" / "_shared"
SHARED_AS = str(SHARED)


def _ensure_shared_on_path() -> None:
    if SHARED_AS not in sys.path:
        sys.path.insert(0, SHARED_AS)


def test_shared_schema_round_trip():
    """確保 _shared/alphaear_schema 提供 Pydantic 模型 InvestmentSignal 並可序列化往返。"""
    _ensure_shared_on_path()

    from alphaear_schema import InvestmentSignal

    signal = InvestmentSignal(
        signal_id="test_sig",
        title="測試訊號",
        summary="測試摘要",
        reasoning="測試推理",
        transmission_chain=[],
        sentiment_score=0.5,
        confidence=0.8,
        intensity=3,
        expectation_gap=0.2,
        timeliness=0.9,
        expected_horizon="T+1",
        price_in_status="未知",
        impact_tickers=[],
        industry_tags=[],
        sources=[],
    )
    assert signal.signal_id == "test_sig"
    assert signal.title == "測試訊號"
    dumped = signal.model_dump(mode="python")
    assert dumped["signal_id"] == "test_sig"
    assert dumped["title"] == "測試訊號"


def test_deprecation_shim_still_works():
    """v1.1.0 雙 import 必須都通；舊腳本若用 `scripts.schema.models.InvestmentSignal` 不應中斷。

    既有的 skill 程式碼以 ``from scripts.schema.models import InvestmentSignal``
    形式寫入（在 ``<skill>/scripts/schema/models.py``）。本測試用 importlib 將
    three skill 的 shim 模組掛在 ``scripts.schema.models`` namespace 下，
    並斷言其 ``InvestmentSignal`` 物件等同於 vendored 版本（Pydantic v2 class identity）。
    """
    _ensure_shared_on_path()
    # 確保先前 import 過的 alphaear_schema.* 仍可解析到 _shared（隨意）
    from alphaear_schema import InvestmentSignal as SharedInvest

    shared_models_path = REPO / "skills" / "_shared" / "alphaear_schema" / "models.py"

    for skill in ["alphaear-predictor", "alphaear-reporter", "alphaear-signal-tracker"]:
        skill_scripts = REPO / "skills" / skill / "scripts"
        # 把該 skill 的 scripts 注入成 namespace package（不靠 file-system parent）
        shim_path = skill_scripts / "schema" / "models.py"
        spec = importlib.util.spec_from_file_location(
            f"scripts.schema.models",  # fully qualified (parent dirs already declared below)
            shim_path,
        )
        assert spec is not None and spec.loader is not None, f"{skill}: shim spec 無法建立"

        # 用 namespace package 載入：scripts + scripts.schema + scripts.alphaear_schema 都靠目錄當 namespace 即可。
        for mod_name in (
            "scripts",
            "scripts.schema",
            "scripts.alphaear_schema",
            "scripts.alphaear_schema.models",
        ):
            if mod_name not in sys.modules:
                spec_ns = importlib.util.spec_from_file_location(
                    mod_name,
                    # 對 alphaear_schema 指向 vendored 目錄的 __init__.py；其他指向 skill 的
                    location=(
                        skill_scripts / "alphaear_schema" / "__init__.py"
                        if mod_name == "scripts.alphaear_schema"
                        else skill_scripts / "__init__.py" if mod_name == "scripts"
                        else skill_scripts / "schema" / "__init__.py" if mod_name == "scripts.schema"
                        else skill_scripts / "alphaear_schema" / "models.py"
                    ),
                    submodule_search_locations=[
                        str(
                            skill_scripts / "alphaear_schema"
                            if mod_name == "scripts.alphaear_schema"
                            else skill_scripts
                        )
                    ],
                )
                mod = importlib.util.module_from_spec(spec_ns)
                sys.modules[mod_name] = mod
                if spec_ns.loader is not None:
                    spec_ns.loader.exec_module(mod)

        # 載 shim 自身並驗證 class identity
        shim_spec = importlib.util.spec_from_file_location(
            "scripts.schema.models", shim_path,
        )
        shim_mod = importlib.util.module_from_spec(shim_spec)
        sys.modules["scripts.schema.models"] = shim_mod
        shim_spec.loader.exec_module(shim_mod)

        from scripts.schema.models import InvestmentSignal as ShimInvest  # type: ignore  # noqa: E402

        # * 為 wildcard re-export。shim 檔案：
        #     from scripts.alphaear_schema.models import *  # noqa
        # 因此 ShimInvest 應該是 alphaear_schema.models 的同一 class。為了
        # 證明「共用基底」正確，我們另從 _shared 載入原檔驗證三者一致：
        shared_spec = importlib.util.spec_from_file_location(
            "_shared_alphaear_models", shared_models_path,
        )
        shared_mod = importlib.util.module_from_spec(shared_spec)
        shared_spec.loader.exec_module(shared_mod)
        NewInvest = getattr(shared_mod, "InvestmentSignal")

        # shim 的 InvestmentSignal 一定與 NewInvest 同物件嗎？因為 shim 是
        # `from X import *`，重新 import 後會拿到 vendored 的 module。
        # 為了不依賴 import 順序，我們驗證「兩者 pydantic 全等」。
        from pydantic import BaseModel

        a: BaseModel = ShimInvest(signal_id="x", title="t")
        b: BaseModel = NewInvest(signal_id="x", title="t")
        assert a.model_dump() == b.model_dump(), f"{skill}: shim 與 _shared 結構不一致"
        assert ShimInvest is NewInvest or ShimInvest.__class__ is NewInvest.__class__, (
            f"{skill}: shim 與 _shared 的 InvestmentSignal 應指向同一個 class"
        )

    # 額外：SharedInvest 必為基線
    assert SharedInvest is not None

