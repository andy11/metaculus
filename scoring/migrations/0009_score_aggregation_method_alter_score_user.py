# Generated by Django 5.0.8 on 2024-08-21 20:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0008_alter_score_question"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="score",
            name="aggregation_method",
            field=models.CharField(
                choices=[
                    ("recency_weighted", "Recency Weighted"),
                    ("unweighted", "Unweighted"),
                    ("single_aggregation", "Single Aggregation"),
                ],
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="score",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
