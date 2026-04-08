from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BackupSnapshot(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="backup_snapshot")
    favorite_songs = models.JSONField(default=list, blank=True)
    playlists = models.JSONField(default=list, blank=True)
    downloaded_songs = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BackupSnapshot<{self.user.email}>"
