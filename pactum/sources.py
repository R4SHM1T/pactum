"""Load the data a contract points at into a pandas DataFrame."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .contracts import Contract, ContractError, SourceSpec


def load_source(source: SourceSpec, base_dir: Path) -> pd.DataFrame:
    if source.path is None:
        raise ContractError("contract source has no 'path'")
    path = Path(source.path)
    if not path.is_absolute():
        path = base_dir / path
    if source.type == "csv":
        return pd.read_csv(path, **source.options)
    if source.type == "parquet":
        return pd.read_parquet(path, **source.options)
    raise ContractError(f"unsupported source type: {source.type}")


def load_for_contract(contract: Contract) -> pd.DataFrame:
    if contract.source is None:
        raise ContractError(f"contract '{contract.name}' has no source to load")
    return load_source(contract.source, contract.base_dir)
