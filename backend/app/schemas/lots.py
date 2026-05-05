from datetime import datetime

from pydantic import BaseModel, computed_field


class WaferSummary(BaseModel):
    id: int
    wafer_code: str
    started_at: datetime | None
    finished_at: datetime | None
    total_parts: int = 0
    pass_parts: int = 0

    @computed_field
    @property
    def fail_rate(self) -> float:
        if self.total_parts == 0:
            return 0.0
        return round((self.total_parts - self.pass_parts) / self.total_parts, 4)

    model_config = {"from_attributes": True}


class LotSummary(BaseModel):
    id: int
    lot_code: str
    product_type: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    wafer_count: int = 0
    total_parts: int = 0
    pass_parts: int = 0

    @computed_field
    @property
    def fail_rate(self) -> float:
        if self.total_parts == 0:
            return 0.0
        return round((self.total_parts - self.pass_parts) / self.total_parts, 4)

    model_config = {"from_attributes": True}


class LotDetail(LotSummary):
    wafers: list[WaferSummary] = []


class MeasurementResponse(BaseModel):
    id: int
    part_id: int
    test_id: int
    test_num: int | None = None
    test_name: str | None = None
    unit: str | None = None
    result: float | None
    is_pass: bool
    is_alarm: bool
    created_at: datetime

    model_config = {"from_attributes": True}
