from shims.registry import ShimRegistry
from shims import BaseShim


def test_shim_registry_initialization():
    all_shims = [
        "git",
        "rest_api",
        "database",
        "knowledge_base",
        "support_desk",
        "social_media",
        "vector_db",
        "cicd",
        "iot",
        "security",
        "filesystem",
        "email",
        "calendar",
        "payment",
        "notification",
        "search",
        "analytics",
        "workflow",
        "compliance",
        "hitl",
    ]
    registry = ShimRegistry(enabled_shims=all_shims)
    assert len(registry.shims) == 20

    for name, shim in registry.shims.items():
        assert isinstance(shim, BaseShim)
        assert shim.name == name
        assert shim.description

        # Test reset
        shim.reset()

        # Test tool specs
        specs = shim.get_tool_specs()
        assert isinstance(specs, list)
        for spec in specs:
            assert len(spec) == 3
            assert callable(spec[1])

    registry.shutdown_all()


def test_database_shim():
    registry = ShimRegistry(enabled_shims=["database"])
    db = registry.shims["database"]

    # Test query
    res = db.query("SELECT * FROM accounts")
    assert len(res) > 0
    assert res[0]["name"] == "Main Operating"

    # Test insert
    db.insert("accounts", {"id": 3, "name": "Test Account", "balance": 100.0})
    res = db.query("SELECT * FROM accounts WHERE id=3")
    assert res[0]["name"] == "Test Account"

    # Test update
    db.update("accounts", {"balance": 200.0}, "id=3")
    res = db.query("SELECT * FROM accounts WHERE id=3")
    assert res[0]["balance"] == 200.0

    # Test delete
    db.delete("accounts", "id=3")
    res = db.query("SELECT * FROM accounts WHERE id=3")
    assert len(res) == 0

    registry.shutdown_all()


def test_filesystem_shim():
    registry = ShimRegistry(enabled_shims=["filesystem"])
    fs = registry.shims["filesystem"]

    # Test write/read
    fs.write_file("test.txt", "hello world")
    content = fs.read_file("test.txt")
    assert content == "hello world"

    # Test list
    files = fs.list_dir(".")
    assert "test.txt" in files

    # Test delete
    fs.delete("test.txt")
    files = fs.list_dir(".")
    assert "test.txt" not in files

    registry.shutdown_all()
