from fieldworkimport.qgis_plugin_tools.tools.resources import plugin_name

# TODO: Look into this https://reinvantveer.github.io/2021/04/10/qgis-plugin-development.html


def test_plugin_name():
    assert plugin_name() == "FieldworkImport"
