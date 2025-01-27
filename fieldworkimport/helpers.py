from contextlib import contextmanager
from typing import Any

from qgis.core import NULL, QgsApplication, QgsAuthMethodConfig, QgsDataSourceUri, QgsProject, QgsVectorLayer
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


def get_layers_by_table_name(schema: str, table_name: str, *, no_filter: bool = False, raise_exception: bool = False) -> list[QgsVectorLayer]:
    layers_dict: dict[str, QgsVectorLayer] = QgsProject.instance().mapLayers()  # type: ignore
    layers_list = layers_dict.values()

    matches = []

    src_snippet = f'table="{schema}"."{table_name}"'

    for layer in layers_list:
        if no_filter and layer.subsetString():
            continue
        src_str = layer.source()
        if src_snippet in src_str:
            matches.append(layer)

    if not matches and raise_exception:
        msg = f"Could not find layer with table '{schema}'.'{table_name}'."
        raise ValueError(msg)
    return matches
