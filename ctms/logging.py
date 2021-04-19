"""Logging configuration"""

import logging
import logging.config

import uvicorn
from dockerflow.logging import JsonLogFormatter


class UvicornJsonLogFormatter(JsonLogFormatter):
    """Dockerflow JsonLogFormatter, with special handling for uvicorn scope."""

    DROP_FIELDS = {
        "color_message",
    }
    DROP_SCOPE_FIELDS = {
        "root_path",  # FastAPI proxy path
        "raw_path",  # Uvicorn path as bytes
    }
    SECURITY_HEADERS = {
        "cookie",  # CSRF token, not needed in logs
        "authorization",  # Basic auth or OAuth2 bearer tokens
    }

    def __init__(self, log_dropped_fields=False, **kwargs):
        """
        Initialize the UvicornJsonLogFormatter.

        Adds one extra parameter to JsonLogFormatter:

        * log_dropped_fields: Add "dropped_fields" list to log context.

        These fields are dropped because they tend to be class instances that
        are not useful for logging. This setting could be used in production
        to detect when the interface changes, and a new useful field is
        available.
        """
        super().__init__(**kwargs)
        self.log_dropped_fields = log_dropped_fields

    def convert_record(self, record):
        """
        Convert a Python LogRecord attribute into a dict that follows MozLog
        application logging standard, with special processing of the Fields
        data added by uvicorn.

        * from - https://docs.python.org/3/library/logging.html#logrecord-attributes
        * to - https://wiki.mozilla.org/Firefox/Services/Logging
        """
        out = super().convert_record(record)
        fields_in = out.get("Fields", {})
        out["Fields"] = self.convert_fields(fields_in)
        return out

    def convert_fields(self, fields):
        """Convert the raw uvicorn Fields dictionary to more useful data."""
        out = {}
        dropped = []
        is_bytes = []
        for field_key, field_value in fields.items():
            if field_key in self.DROP_FIELDS:
                if self.log_dropped_fields:
                    dropped.append(field_key)
            elif field_key == "scope":
                # Lift up relevant request details from scope, drop irrelevant details
                for key, value in field_value.items():
                    if key in self.DROP_SCOPE_FIELDS:
                        if self.log_dropped_fields:
                            dropped.append(f"scope.{key}")
                    elif key == "headers":
                        headers, byte_fields, have_dupes = self.convert_headers(value)
                        out["headers"] = headers
                        if have_dupes:
                            out["headers_have_duplicates"] = True
                        is_bytes.extend(
                            f"headers{'.' if hfield else ''}{hfield}"
                            for hfield in byte_fields
                        )
                    elif key == "state":
                        # Import log context from CTMS
                        for skey, sval in value.get("log_context", {}).items():
                            out[skey] = sval
                    elif key == "endpoint" and hasattr(value, "__name__"):
                        out["endpoint"] = value.__name__  # Endpoint function
                    elif (
                        key in ("client", "server")
                        and isinstance(value, list)
                        and len(value) == 2
                    ):
                        out[f"{key}_ip"], out[f"{key}_port"] = value
                    elif key == "path_params" and isinstance(value, dict):
                        # Dictionary of path parameters
                        out["path_params"] = value
                    elif isinstance(value, bytes):
                        # HTTP values are probably ASCII, try converting
                        clean_value, decoded = self.attempt_to_decode_bytestring(value)
                        out[key] = clean_value
                        if not decoded:
                            is_bytes.append(key)
                    elif isinstance(value, str):
                        out[key] = value
                    elif self.log_dropped_fields:
                        dropped.append(f"scope.{key}")
            else:
                out[field_key] = field_value
        if dropped:
            out["dropped_fields"] = sorted(dropped)
        if is_bytes:
            out["bytes_fields"] = sorted(is_bytes)
        return out

    def attempt_to_decode_bytestring(self, string):
        """
        Attempt to decode a bytestring as ASCII string

        Return is two elements:
        * The converted or original string
        * True if the output is a string, False if original
        """
        if isinstance(string, str):
            return string, True

        if isinstance(string, bytes):
            try:
                out = string.decode("ascii")
            except:  # pylint: disable=bare-except
                # Handle Python bugs like #31825
                return string, False
            else:
                return out, True
        else:
            return string, False

    def convert_headers(self, headers):
        """
        Convert uvicorn raw headers

        Actions:
        * Omit the values from security headers
        * Attempt to convert header names and values to strings
        * Turn into a dictionary of header to values, or list of
          values when multiple headers returned

        Return is tuple:
        * headers dict
        * list of fields with bytes, or empty string if a header name is bytes
        * True if any header was provided twice
        """
        # Process bytestring headers, omit security details
        new_headers = {}
        byte_fields = []
        has_duplicates = False

        for header_name, header_val in headers:
            header_name, header_decoded = self.attempt_to_decode_bytestring(header_name)
            if not header_decoded:
                byte_fields.append("")
            if header_name in self.SECURITY_HEADERS:
                clean_val = "[OMITTED]"
            else:
                clean_val, decoded = self.attempt_to_decode_bytestring(header_val)
                if header_decoded and not decoded:
                    byte_fields.append(header_name)
            if header_name in new_headers:
                has_duplicates = True
                old_value = new_headers[header_name]
                if isinstance(old_value, list):
                    new_value = old_value
                else:
                    new_value = [old_value]
                new_value.append(clean_val)
                new_headers[header_name] = new_value
            else:
                new_headers[header_name] = clean_val
        return new_headers, byte_fields, has_duplicates


def configure_logging(use_mozlog=True, logging_level="INFO"):
    """Configure Python logging.

    :param use_mozlog: If True, use MozLog format, appropriate for deployments.
        If False, format logs for human consumption.
    :param logging_level: The logging level, such as DEBUG or INFO.
    """

    # Processors used for logs generated by stdlib's logging
    uvicorn_formatters = uvicorn.config.LOGGING_CONFIG["formatters"]
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "dev_console": {
                "format": "%(asctime)s %(levelname)s:%(name)s:  %(message)s"
            },
            "mozlog_json": {
                "()": "ctms.logging.JsonLogFormatter",
                "logger_name": "ctms",
            },
            "uvicorn_access": uvicorn_formatters["access"],
            "uvicorn_default": uvicorn_formatters["default"],
            "uvicorn_mozlog": {
                "()": "ctms.logging.UvicornJsonLogFormatter",
                "logger_name": "ctms",
            },
        },
        "handlers": {
            "humans": {
                "class": "logging.StreamHandler",
                "formatter": "dev_console",
                "level": "DEBUG",
            },
            "mozlog": {
                "class": "logging.StreamHandler",
                "formatter": "mozlog_json",
                "level": "DEBUG",
            },
            "uvicorn.access": {
                "class": "logging.StreamHandler",
                "formatter": "uvicorn_access",
                "level": "INFO",
            },
            "uvicorn.default": {
                "class": "logging.StreamHandler",
                "formatter": "uvicorn_default",
                "level": "INFO",
            },
            "uvicorn.mozlog": {
                "class": "logging.StreamHandler",
                "formatter": "uvicorn_mozlog",
                "level": "INFO",
            },
        },
        "loggers": {
            "alembic": {
                "propagate": False,
                "handlers": ["mozlog" if use_mozlog else "humans"],
                "level": logging_level,
            },
            "ctms": {
                "propagate": False,
                "handlers": ["mozlog" if use_mozlog else "humans"],
                "level": logging_level,
            },
            "uvicorn": {
                "handlers": ["uvicorn.mozlog" if use_mozlog else "uvicorn.default"],
                "level": logging_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["uvicorn.mozlog" if use_mozlog else "uvicorn.default"],
                "level": logging_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["uvicorn.mozlog" if use_mozlog else "uvicorn.access"],
                "level": logging_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["mozlog" if use_mozlog else "humans"],
            "level": "WARNING",
        },
    }
    logging.config.dictConfig(logging_config)
