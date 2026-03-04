from typing import List
from pydantic import BaseModel


class HwpxBlock(BaseModel):
    block_id: str
    type: str
    text: str


class HwpxReadResponse(BaseModel):
    file_name: str
    blocks: List[HwpxBlock]


class ModificationItem(BaseModel):
    block_id: str
    target_text: str
    replace_text: str


class HwpxModifyRequest(BaseModel):
    modifications: List[ModificationItem]
