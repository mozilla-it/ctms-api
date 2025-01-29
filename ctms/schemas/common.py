from datetime import datetime
from typing import Annotated

from pydantic import AnyUrl, BeforeValidator, PlainSerializer, TypeAdapter

http_url_adapter = TypeAdapter(AnyUrl)

AnyUrlString = Annotated[str, BeforeValidator(lambda value: str(http_url_adapter.validate_python(value)))]


ZeroOffsetDatetime = Annotated[datetime, PlainSerializer(lambda dt: dt.isoformat())]
