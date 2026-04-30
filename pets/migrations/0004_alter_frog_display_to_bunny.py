from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pets", "0003_seed_default_pets"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pet",
            name="pet_type",
            field=models.CharField(
                choices=[("cat", "Cat"), ("dog", "Dog"), ("frog", "Bunny")],
                max_length=20,
            ),
        ),
    ]
