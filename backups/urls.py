from django.urls import path

from .views import BulkRestoreBackupView, BulkUploadBackupView, MyBackupView

urlpatterns = [
    path("me/", MyBackupView.as_view(), name="my_backup"),
    path("bulk-upload/", BulkUploadBackupView.as_view(), name="backup_bulk_upload"),
    path("bulk-restore/", BulkRestoreBackupView.as_view(), name="backup_bulk_restore"),
]
