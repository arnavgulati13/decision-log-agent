from pydantic import BaseModel
from pydantic import Field

class DecisionLog(BaseModel):
    decision: str = Field(description="The decision that was made.")
    project: str = Field(description="The project that this decision belongs to.")
    rationale: str = Field(description="The rationale or reasoning behind the decision.")
