import json
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from textual.widgets import TextLog


class TpuType(str, Enum):
    v2 = "v2"
    v3 = "v3"
    v4 = "v4"
    v2_pod = "v2_pod"
    v3_pod = "v3_pod"
    v4_pod = "v4_pod"
    all = "all"
    any = "all"


class TpuVm(BaseModel):
    type: str = Field(...)
    name: str = Field(...)
    zone: str = Field(...)
    ipAddress: str = Field(...)
    externalIp: str = Field(...)

    @classmethod
    def load_json(cls, tpu_file: Path, kind: Optional[str] = None, encoding: str = "utf-8") -> List["TpuVm"]:
        tpu_vms = [cls.parse_obj(x) for x in json.loads(tpu_file.read_text(encoding=encoding))]
        return [x for x in tpu_vms if (kind is None or kind == "all" or x.type == kind)]
