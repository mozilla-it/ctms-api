from pydantic import BaseModel


class ComparableBase(BaseModel):
    def equivalent(self, other):
        if not isinstance(other, ComparableBase):
            return False

        # We exclude these fields in general because they are
        # generated server-side and not useful
        # for comparison in most cases. Check directly
        # that these fields are equivalent if you want
        # to do that
        excluded_in_comparison = {"create_timestamp", "update_timestamp"}

        return self.dict(exclude=excluded_in_comparison) == other.dict(
            exclude=excluded_in_comparison
        )
