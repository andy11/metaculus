from django.contrib import admin

from projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ["type", "name"]
    autocomplete_fields = ["created_by"]
