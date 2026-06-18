from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger


class PulseCareLogDefaults(logging.Filter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = getattr(record, "service", self.service_name)
        for field in (
            "event",
            "trace_id",
            "device_id",
            "region",
            "latency_ms",
            "error_type",
            "error_message",
        ):
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


def configure_json_logging(service_name: str) -> None:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(service)s %(event)s "
        "%(trace_id)s %(device_id)s %(region)s %(latency_ms)s %(error_type)s %(error_message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(PulseCareLogDefaults(service_name))
    logger.addHandler(handler)
    logging.getLogger("uvicorn.access").handlers.clear()
