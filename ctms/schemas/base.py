from pydantic import BaseModel


class ComparableBase(BaseModel):
    def is_default(self):
        return len(self.model_dump(exclude_defaults=True)) == 0
