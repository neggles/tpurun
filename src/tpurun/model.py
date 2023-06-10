import json
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class TpuType(str, Enum):
    v2 = "v2"
    v3 = "v3"
    v4 = "v4"
    v2_pod = "v2_pod"
    v3_pod = "v3_pod"
    v4_pod = "v4_pod"
    all = "all"


class TpuVm(BaseModel):
    type: str = Field(...)
    name: str = Field(...)
    zone: str = Field(...)
    ipAddress: str = Field(...)
    externalIp: str = Field(...)

    @property
    def number(self) -> int:
        return int(self.name.replace(f"{self.type}-node-", ""))

    @classmethod
    def load_json(
        cls,
        tpu_file: Path,
        kind: Optional[str] = None,
        nodes: Optional[List[int]] = None,
        encoding: str = "utf-8",
    ) -> List["TpuVm"]:
        tpu_vms = [cls.parse_obj(x) for x in json.loads(tpu_file.read_text(encoding=encoding))]
        return cls.filter_tpu_vms(tpu_vms, kind=kind, nodes=nodes)

    @classmethod
    def filter_tpu_vms(
        cls,
        tpu_vms: List["TpuVm"],
        kind: Optional[TpuType] = TpuType.all,
        nodes: Optional[List[int]] = None,
    ) -> List["TpuVm"]:
        if kind == TpuType.all:
            if nodes is not None:
                raise ValueError("Cannot filter by node number without specifying node type")
            return tpu_vms
        if nodes is None:
            return [x for x in tpu_vms if x.type == kind.value]
        else:
            return [x for x in tpu_vms if x.type == kind.value and x.number in nodes]
