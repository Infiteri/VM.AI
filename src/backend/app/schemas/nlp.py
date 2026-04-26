from pydantic import BaseModel, Field
from typing import Any, Optional, List

from app.schemas.task import TaskPayload


# ================================================================================
# NlpPayloadField - Single field with {value, predicted}
# ================================================================================

class NlpPayloadField(BaseModel):
    """
    Single field with value and predicted flag.
    Value can be: str, list[str], int, float, datetime, None
    """

    value: Any = None
    predicted: bool = True


# ================================================================================
# NlpAddPayload - For predict_nlp_add() input
# ================================================================================

class NlpAddPayload(BaseModel):
    """
    NLP payload structure for predict_nlp_add().
    Contains all fields with {value, predicted} wrapper.
    """

    name: NlpPayloadField
    start: NlpPayloadField
    deadline: NlpPayloadField
    difficulty: NlpPayloadField
    duration: NlpPayloadField
    category: NlpPayloadField
    location: NlpPayloadField
    importance: NlpPayloadField
    fixed_time: NlpPayloadField
    fixed_start: NlpPayloadField


# ================================================================================
# NlpChangedFields - For merge_nlp_modify() input
# ================================================================================

class NlpChangedFields(BaseModel):
    """
    Changed fields for NLP modify flow.
    Similar structure to NlpAddPayload but all fields are optional.
    """

    name: Optional[NlpPayloadField] = None
    start: Optional[NlpPayloadField] = None
    deadline: Optional[NlpPayloadField] = None
    difficulty: Optional[NlpPayloadField] = None
    duration: Optional[NlpPayloadField] = None
    category: Optional[NlpPayloadField] = None
    location: Optional[NlpPayloadField] = None
    importance: Optional[NlpPayloadField] = None
    fixed_time: Optional[NlpPayloadField] = None
    fixed_start: Optional[NlpPayloadField] = None