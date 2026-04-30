from django.db import migrations


PET_TYPES = {
    "dog": "Dog",
    "cat": "Cat",
    "frog": "Bunny",
}
MOODS = {
    "neutral": "Neutral",
    "focused": "Focused",
    "happy": "Happy",
    "tired": "Tired",
}


def seed_default_pets(apps, schema_editor):
    Pet = apps.get_model("pets", "Pet")

    for pet_type, label in PET_TYPES.items():
        for level in range(1, 4):
            for mood, mood_label in MOODS.items():
                Pet.objects.get_or_create(
                    pet_type=pet_type,
                    level=level,
                    mood=mood,
                    defaults={
                        "name": label,
                        "svg_path": f"pets/{pet_type}-{level}-{mood}.svg",
                    },
                )


class Migration(migrations.Migration):

    dependencies = [
        ("pets", "0002_alter_pet_options_alter_pet_unique_together_pet_mood_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_default_pets, migrations.RunPython.noop),
    ]
