from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from journal.activity_ingest import persist_sessions_for_date


def run_collector(user_id=None, date_str=None, base_dir=None) -> dict | None:
    if user_id is None:
        return None

    if date_str is None:
        date_str = timezone.localdate().isoformat()

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist as exc:
        raise CommandError(f"User {user_id} does not exist.") from exc

    return persist_sessions_for_date(user, date_str, base_dir=base_dir)


class Command(BaseCommand):
    help = "Collect frontmost macOS app activity and write daily JSON logs."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int)
        parser.add_argument("--date")
        parser.add_argument("--base-dir")

    def handle(self, *args, **options):
        if not any(options.get(key) for key in ("user_id", "date", "base_dir")):
            result = run_collector()
        else:
            result = run_collector(
                user_id=options.get("user_id"),
                date_str=options.get("date"),
                base_dir=options.get("base_dir"),
            )
        if isinstance(result, dict):
            self.stdout.write(
                self.style.SUCCESS(
                    "Synced "
                    f"{len(result['activities'])} sessions "
                    f"({result['created_count']} created, "
                    f"{result['updated_count']} updated)."
                )
            )
