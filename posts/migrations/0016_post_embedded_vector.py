# Generated by Django 5.0.6 on 2024-07-19 16:12

import pgvector.django.vector
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0015_embeds_vector"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="embedding_vector",
            field=pgvector.django.vector.VectorField(
                blank=True,
                help_text="Vector embeddings (clip-vit-large-patch14) of the file content",
                null=True,
            ),
        ),
    ]
