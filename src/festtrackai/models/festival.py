from pydantic import BaseModel, Field

class Festival(BaseModel):
    """Pydantic validation model for a festival record with tiered and absolute deadlines."""
    name: str = Field(..., min_length=1, description="Name of the film festival")
    fee: float = Field(..., ge=0.0, description="Submission fee in USD")
    tier_deadline: str = Field(..., description="Deadline for the current fee tier / early bird")
    absolute_deadline: str = Field(..., description="Final absolute submission deadline")
    status: str = Field(default="Unapplied", description="Current application status")