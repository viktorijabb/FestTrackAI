from pydantic import BaseModel, Field, ConfigDict


class Festival(BaseModel):
    """Submission metadata; None means fee unknown, zero means explicitly free."""
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(..., min_length=1)
    fee: float | None = Field(default=None, ge=0.0, allow_inf_nan=False,
                              description="Submission fee in USD; null when unknown")
    tier_deadline: str = Field(default="TBD", min_length=1)
    absolute_deadline: str = Field(default="TBD", min_length=1)
    status: str = "Unapplied"
