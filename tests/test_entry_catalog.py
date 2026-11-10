import unittest

from scripts.entry_catalog import (
    file_kind,
    normalize_entry,
    parse_where,
    select_representatives,
)


class EntryCatalogTests(unittest.TestCase):
    def test_failed_entry_keeps_selection_dimensions_without_results(self):
        row = normalize_entry(
            {
                "entry_id": "failed-a",
                "upload_id": "upload-1",
                "main_author": {"name": "Alice"},
                "parser_name": "parsers/lammps",
                "mainfile": "runs/123/poscar_1444.data",
                "processed": False,
                "processing_errors": ["process failed"],
            },
            "LAMMPS",
        )
        self.assertEqual(row["status"], "unprocessed")
        self.assertIsNone(row["workflow_name"])
        self.assertEqual(row["mainfile_kind"], "data")
        self.assertEqual(row["mainfile_pattern"], "poscar_#.data")
        self.assertEqual(row["processing_error"], "process failed")

    def test_workflow_list_and_log_names_are_normalized(self):
        row = normalize_entry(
            {
                "entry_id": "processed-a",
                "main_author": {"name": "Bob"},
                "mainfile": "solvate/log.DADA+1000",
                "processed": True,
                "results": {"method": {"workflow_name": ["molecular_dynamics"]}},
            },
            "LAMMPS",
        )
        self.assertEqual(row["workflow_name"], "molecular_dynamics")
        self.assertEqual(row["mainfile_kind"], "log")
        self.assertEqual(file_kind("other/std.out"), "output")

    def test_deterministic_selection_by_author_and_file_kind(self):
        rows = [
            {"entry_id": "a", "status": "unprocessed", "main_author": "Alice", "mainfile_kind": "log"},
            {"entry_id": "b", "status": "unprocessed", "main_author": "Alice", "mainfile_kind": "log"},
            {"entry_id": "c", "status": "unprocessed", "main_author": "Alice", "mainfile_kind": "data"},
            {"entry_id": "d", "status": "processed", "main_author": "Alice", "mainfile_kind": "log"},
            {"entry_id": "e", "status": "unprocessed", "main_author": "Bob", "mainfile_kind": "log"},
        ]
        args = dict(status="unprocessed", group_by=["main_author", "mainfile_kind"], where={}, seed=0)
        first = select_representatives(rows, **args)
        second = select_representatives(reversed(rows), **args)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual(sum(row["bucket_entry_count"] for row in first), 4)
        self.assertNotIn("d", {row["entry_id"] for row in first})
        filtered = select_representatives(
            rows, status="unprocessed", group_by=["main_author"],
            where=parse_where(["mainfile_kind=data"]), seed=0,
        )
        self.assertEqual([row["entry_id"] for row in filtered], ["c"])


if __name__ == "__main__":
    unittest.main()
