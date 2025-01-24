from contextlib import contextmanager
from typing import Any

from qgis.core import NULL, QgsApplication, QgsAuthMethodConfig, QgsDataSourceUri, QgsVectorLayer
from qgis.PyQt.QtSql import QSqlDatabase


@contextmanager
def layer_database_connection(layer: QgsVectorLayer):
    # Get the data source URI from the layer
    uri = QgsDataSourceUri(layer.dataProvider().dataSourceUri())  # type: ignore

    # Set up the database connection using the layer's connection details
    db = QSqlDatabase.addDatabase("QPSQL")  # Use the QPSQL driver for PostGIS
    db.setHostName(uri.host())  # Database host
    db.setPort(int(uri.port()))  # Database port (default 5432)
    db.setDatabaseName(uri.database())  # Database name
    db.setUserName(uri.username())  # Username
    db.setPassword(uri.password())  # Password
    db.setConnectOptions()

    layer.dataProvider()

    authcfg_id = uri.authConfigId()
    if authcfg_id:
        mgr = QgsApplication.authManager()
        assert mgr  # noqa: S101
        authcfg = QgsAuthMethodConfig()
        mgr.loadAuthenticationConfig(authcfg_id, authcfg, True)  # noqa: FBT003
        auth_info = authcfg.configMap()
        db.setUserName(auth_info["username"])
        db.setPassword(auth_info["password"])

    if not db.open():
        err = db.lastError()
        raise ValueError(err)

    try:
        yield db
    finally:
        db.close()


def not_NULL(val: Any) -> bool:  # noqa: ANN401, D103, N802
    return not (val is None or val == NULL)
