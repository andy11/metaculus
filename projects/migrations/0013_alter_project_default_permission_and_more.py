# Generated by Django 5.0.6 on 2024-06-26 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0012_project_leaderboard_type_alter_project_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="default_permission",
            field=models.CharField(
                blank=True,
                choices=[
                    ("viewer", "Viewer"),
                    ("forecaster", "Forecaster"),
                    ("curator", "Curator"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                default="forecaster",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="projectuserpermission",
            name="permission",
            field=models.CharField(
                choices=[
                    ("viewer", "Viewer"),
                    ("forecaster", "Forecaster"),
                    ("curator", "Curator"),
                    ("admin", "Admin"),
                ],
                db_index=True,
            ),
        ),
    ]
