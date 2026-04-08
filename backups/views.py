from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BackupSnapshot
from .serializers import BackupSnapshotSerializer


def _ensure_list(value, field_name):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError({field_name: [f"{field_name} must be a list."]})
    return value


def _dedupe_items(items):
    seen_keys = set()
    result = []
    for item in items:
        if isinstance(item, dict) and item.get("id") is not None:
            key = f"id:{item.get('id')}"
        else:
            key = str(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        result.append(item)
    return result


class MyBackupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        snapshot, _ = BackupSnapshot.objects.get_or_create(user=request.user)
        serializer = BackupSnapshotSerializer(snapshot)
        return Response(serializer.data)

    def put(self, request):
        snapshot, _ = BackupSnapshot.objects.get_or_create(user=request.user)
        serializer = BackupSnapshotSerializer(snapshot, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class BulkUploadBackupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        snapshot, _ = BackupSnapshot.objects.get_or_create(user=request.user)

        mode = str(request.data.get("mode", "append")).lower().strip()
        if mode not in {"append", "replace"}:
            raise ValidationError({"mode": ["mode must be either 'append' or 'replace'."]})

        favorites = _ensure_list(request.data.get("favorite_songs"), "favorite_songs")
        playlists = _ensure_list(request.data.get("playlists"), "playlists")
        downloads = _ensure_list(request.data.get("downloaded_songs"), "downloaded_songs")

        if mode == "replace":
            snapshot.favorite_songs = _dedupe_items(favorites)
            snapshot.playlists = _dedupe_items(playlists)
            snapshot.downloaded_songs = _dedupe_items(downloads)
        else:
            snapshot.favorite_songs = _dedupe_items((snapshot.favorite_songs or []) + favorites)
            snapshot.playlists = _dedupe_items((snapshot.playlists or []) + playlists)
            snapshot.downloaded_songs = _dedupe_items(
                (snapshot.downloaded_songs or []) + downloads
            )

        snapshot.save(
            update_fields=["favorite_songs", "playlists", "downloaded_songs", "updated_at"]
        )

        serializer = BackupSnapshotSerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BulkRestoreBackupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        snapshot, _ = BackupSnapshot.objects.get_or_create(user=request.user)

        include = request.data.get("include", ["favorite_songs", "playlists", "downloaded_songs"])
        if not isinstance(include, list):
            raise ValidationError({"include": ["include must be a list."]})

        allowed_fields = {"favorite_songs", "playlists", "downloaded_songs"}
        invalid = [item for item in include if item not in allowed_fields]
        if invalid:
            raise ValidationError({"include": [f"Unsupported fields: {', '.join(invalid)}"]})

        response_data = {"updated_at": snapshot.updated_at}
        if "favorite_songs" in include:
            response_data["favorite_songs"] = snapshot.favorite_songs or []
        if "playlists" in include:
            response_data["playlists"] = snapshot.playlists or []
        if "downloaded_songs" in include:
            response_data["downloaded_songs"] = snapshot.downloaded_songs or []

        return Response(response_data, status=status.HTTP_200_OK)
