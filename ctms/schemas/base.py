from pydantic import BaseModel


class ComparableBase(BaseModel):
    def is_default(self):
        return len(self.dict(exclude_defaults=True)) == 0
