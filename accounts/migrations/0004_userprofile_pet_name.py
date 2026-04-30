from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_userprofile_pet_mood"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="pet_name",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
