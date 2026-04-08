from rest_framework import serializers

from .models import BackupSnapshot


class BackupSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSnapshot
        fields = (
            "favorite_songs",
            "playlists",
            "downloaded_songs",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def validate_favorite_songs(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("favorite_songs must be a list.")
        return value

    def validate_playlists(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("playlists must be a list.")
        return value

    def validate_downloaded_songs(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("downloaded_songs must be a list.")
        return value
