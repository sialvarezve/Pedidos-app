from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError


def normalize_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        raise ValidationError({"fecha": "Invalid date format."})

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed
