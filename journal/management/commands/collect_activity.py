from django.core.management.base import BaseCommand


def run_collector() -> None:
    # macOS-specific event wiring will live here later.
    return None


class Command(BaseCommand):
    help = "Collect frontmost macOS app activity and write daily JSON logs."

    def handle(self, *args, **options):
        run_collector()
