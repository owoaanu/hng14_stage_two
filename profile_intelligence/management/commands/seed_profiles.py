import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from profile_intelligence.models import Profile


class Command(BaseCommand):
    help = "Seed profiles from seed_profiles.json without creating duplicates."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=str(settings.BASE_DIR / "seed_profiles.json"),
            help="Path to the seed JSON file. Defaults to seed_profiles.json in BASE_DIR.",
        )

    def handle(self, *args, **options):
        seed_path = Path(options["path"])
        if not seed_path.exists():
            raise CommandError(f"Seed file not found: {seed_path}")

        with seed_path.open("r", encoding="utf-8") as seed_file:
            payload = json.load(seed_file)

        profiles = payload.get("profiles")
        if not isinstance(profiles, list):
            raise CommandError("Seed file must contain a profiles list.")

        created = 0
        updated = 0
        for item in profiles:
            profile, was_created = Profile.objects.update_or_create(
                name=item["name"],
                defaults={
                    "gender": item["gender"].lower(),
                    "gender_probability": item["gender_probability"],
                    "age": item["age"],
                    "age_group": item["age_group"].lower(),
                    "country_id": item["country_id"].upper(),
                    "country_name": item["country_name"],
                    "country_probability": item["country_probability"],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Created {created}, updated {updated}, total {Profile.objects.count()}."
            )
        )
