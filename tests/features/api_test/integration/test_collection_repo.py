from __future__ import annotations

import pytest


class TestCollectionRepository:
    def test_empty_tree(self, collection_repo) -> None:
        tree = collection_repo.load_tree()
        assert tree == []

    def test_create_root_folder(self, collection_repo) -> None:
        node_id = collection_repo.create_node(parent_id="", kind="folder", name="My Folder")
        assert node_id
        tree = collection_repo.load_tree()
        assert len(tree) == 1
        assert tree[0]["name"] == "My Folder"
        assert tree[0]["kind"] == "folder"
        assert tree[0]["expanded"] is True

    def test_create_endpoint_in_folder(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(
            parent_id=folder_id, kind="endpoint", name="Get Users", method="GET", url="/users"
        )
        assert ep_id
        tree = collection_repo.load_tree()
        assert len(tree[0]["children"]) == 1
        child = tree[0]["children"][0]
        assert child["kind"] == "endpoint"
        assert child["method"] == "GET"
        assert child["path"] == "/users"

    def test_create_case_in_endpoint(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(
            parent_id=folder_id, kind="endpoint", name="Get Users", method="GET", url="/users"
        )
        case_id = collection_repo.create_node(
            parent_id=ep_id,
            kind="case",
            name="Test Case",
            request_snapshot={"method": "GET", "url": "/users"},
        )
        assert case_id
        tree = collection_repo.load_tree()
        ep_children = tree[0]["children"][0]["children"]
        assert len(ep_children) == 1
        assert ep_children[0]["kind"] == "case"

    def test_cannot_create_folder_under_endpoint(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(
            parent_id=folder_id, kind="endpoint", name="Get Users", method="GET", url="/users"
        )
        result = collection_repo.create_node(parent_id=ep_id, kind="folder", name="Invalid")
        assert result == ""

    def test_cannot_create_endpoint_under_endpoint(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(
            parent_id=folder_id, kind="endpoint", name="EP1", method="GET", url="/a"
        )
        result = collection_repo.create_node(parent_id=ep_id, kind="endpoint", name="EP2")
        assert result == ""

    def test_rename_node(self, collection_repo) -> None:
        node_id = collection_repo.create_node(parent_id="", kind="folder", name="Old Name")
        collection_repo.rename_node(node_id, "New Name")
        tree = collection_repo.load_tree()
        assert tree[0]["name"] == "New Name"

    def test_rename_empty_name_noop(self, collection_repo) -> None:
        node_id = collection_repo.create_node(parent_id="", kind="folder", name="Keep")
        collection_repo.rename_node(node_id, "   ")
        tree = collection_repo.load_tree()
        assert tree[0]["name"] == "Keep"

    def test_delete_node_removes_children(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="To Delete")
        collection_repo.create_node(parent_id=folder_id, kind="endpoint", name="Child EP")
        collection_repo.delete_node(folder_id)
        tree = collection_repo.load_tree()
        assert tree == []

    def test_set_expanded(self, collection_repo) -> None:
        node_id = collection_repo.create_node(parent_id="", kind="folder", name="Folder")
        collection_repo.set_expanded(node_id, True)
        tree = collection_repo.load_tree()
        assert tree[0]["expanded"] is True

    def test_set_all_expanded(self, collection_repo) -> None:
        collection_repo.create_node(parent_id="", kind="folder", name="A")
        collection_repo.create_node(parent_id="", kind="folder", name="B")
        collection_repo.set_all_expanded(True)
        tree = collection_repo.load_tree()
        assert all(n["expanded"] for n in tree)

    def test_move_node(self, collection_repo) -> None:
        f1 = collection_repo.create_node(parent_id="", kind="folder", name="Folder1")
        f2 = collection_repo.create_node(parent_id="", kind="folder", name="Folder2")
        ep = collection_repo.create_node(parent_id=f1, kind="endpoint", name="EP", method="GET", url="/api")
        collection_repo.move_node(ep, f2)
        tree = collection_repo.load_tree()
        assert len(tree[0]["children"]) == 0
        assert len(tree[1]["children"]) == 1

    def test_move_node_to_descendant_is_blocked(self, collection_repo) -> None:
        f1 = collection_repo.create_node(parent_id="", kind="folder", name="F1")
        ep = collection_repo.create_node(parent_id=f1, kind="endpoint", name="EP")
        # Try to move f1 under ep (ep is a child of f1) — should be blocked
        collection_repo.move_node(f1, ep)
        tree = collection_repo.load_tree()
        assert tree[0]["children"][0]["id"] == ep  # no change

    def test_duplicate_node(self, collection_repo) -> None:
        node_id = collection_repo.create_node(parent_id="", kind="folder", name="Original")
        dup_id = collection_repo.duplicate_node(node_id)
        assert dup_id
        assert dup_id != node_id
        tree = collection_repo.load_tree()
        assert len(tree) == 2
        assert "副本" in tree[1]["name"]

    def test_update_endpoint(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(
            parent_id=folder_id, kind="endpoint", name="Old", method="GET", url="/old"
        )
        collection_repo.update_endpoint(ep_id, "POST", "/new")
        tree = collection_repo.load_tree()
        ep = tree[0]["children"][0]
        assert ep["method"] == "POST"
        assert ep["path"] == "/new"

    def test_save_case_snapshot(self, collection_repo) -> None:
        folder_id = collection_repo.create_node(parent_id="", kind="folder", name="API")
        ep_id = collection_repo.create_node(parent_id=folder_id, kind="endpoint", name="EP", method="GET", url="/api")
        case_id = collection_repo.create_node(
            parent_id=ep_id, kind="case", name="Case"
        )
        collection_repo.save_case_snapshot(case_id, {"method": "POST", "url": "/new"})
        tree = collection_repo.load_tree()
        case = tree[0]["children"][0]["children"][0]
        assert case["requestSnapshot"]["method"] == "POST"

    def test_replace_tree(self, collection_repo) -> None:
        collection_repo.create_node(parent_id="", kind="folder", name="Old")
        new_tree = [
            {
                "id": "new-folder",
                "kind": "folder",
                "name": "New Root",
                "expanded": True,
                "children": [
                    {
                        "id": "new-ep",
                        "kind": "endpoint",
                        "name": "New EP",
                        "method": "DELETE",
                        "path": "/delete-me",
                    }
                ],
            }
        ]
        collection_repo.replace_tree(new_tree)
        tree = collection_repo.load_tree()
        assert len(tree) == 1
        assert tree[0]["name"] == "New Root"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["method"] == "DELETE"
