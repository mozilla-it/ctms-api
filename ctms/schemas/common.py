from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

ZeroOffsetDatetime = Annotated[datetime, PlainSerializer(lambda dt: dt.isoformat())]
