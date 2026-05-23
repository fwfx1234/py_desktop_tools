from __future__ import annotations

from app.plugins.runtime import PluginContext, SimpleQmlRuntime
from app.storage import StorageManager

from .view_model import FtpSftpSshClientViewModel


def _create_view_model(ctx: PluginContext) -> FtpSftpSshClientViewModel:
    storage = ctx.services.storage
    if not isinstance(storage, StorageManager):
        raise RuntimeError("Storage manager is unavailable")
    return FtpSftpSshClientViewModel(storage.database("ftp_sftp_ssh_client.db", check_same_thread=False))


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(_create_view_model)
