from services.agents.blueprint_editor import edit_blueprint


def test_edit_add_react_native():
    bp = {}
    bp = edit_blueprint(bp, "Add React Native app")
    assert bp["frontend"]["framework"] == "react_native"
    assert "ios" in bp["channels"]
    assert "android" in bp["channels"]


def test_edit_switch_to_postgres():
    bp = {}
    bp = edit_blueprint(bp, "use postgres database")
    assert bp["database"]["engine"] == "postgres"
