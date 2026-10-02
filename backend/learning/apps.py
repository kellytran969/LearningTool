"""App configuration for the learning platform."""

from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Learning app config; wires cache-invalidation signals on startup."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "learning"

    def ready(self):
        """Import signal handlers so cache invalidation is registered."""
        from learning import signals  # noqa: F401
