from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
CODE = EXPERIMENT / "code"
BASELINE_CODE = EXPERIMENT.parent / "trace2skill_verusage_baseline_test" / "code"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(BASELINE_CODE))

from global_skill_experiment.construction import (  # noqa: E402
    load_frozen_map,
    preflight,
    save_frozen_map,
)
from skill_evolver.parallel_evolving_agent import (  # noqa: E402
    ParallelSkillEvolver,
    SemanticPatch,
    SemanticPatchItem,
)


class ConstructionTests(unittest.TestCase):
    def test_frozen_map_round_trip_preserves_batch_and_item_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evolver = object.__new__(ParallelSkillEvolver)
            evolver.semantic_item_marker_format = "bracket"
            patches = [
                SemanticPatch(
                    reasoning="one",
                    items=[
                        SemanticPatchItem(
                            target_file="SKILL.md",
                            edit_intent="add one",
                            location_hint="root",
                            change_instruction="retain one",
                        )
                    ],
                    changelog_entries=["one"],
                    batch_index=1,
                ),
                SemanticPatch(
                    reasoning="two",
                    items=[
                        SemanticPatchItem(
                            target_file="SKILL.md",
                            edit_intent="add two",
                            location_hint="root",
                            change_instruction="retain two",
                        )
                    ],
                    changelog_entries=["two"],
                    batch_index=2,
                ),
            ]
            records = [{"instance_id": "train-a"}, {"instance_id": "train-b"}]
            manifest = save_frozen_map(evolver, patches, root, records, batch_size=1)
            loaded, loaded_manifest = load_frozen_map(root)
            self.assertEqual(manifest, loaded_manifest)
            self.assertEqual([1, 2], [patch.batch_index for patch in loaded])
            self.assertEqual(["retain one", "retain two"], [patch.items[0].change_instruction for patch in loaded])

    def test_semantic_preflight_reuses_map_and_makes_zero_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            m_core = root / "m-core"
            m_core.mkdir()
            (m_core / "SKILL.md").write_text("# Core\n", encoding="utf-8")
            memories = root / "memories.json"
            memories.write_text(
                json.dumps([{"instance_id": "train-a"}]) + "\n", encoding="utf-8"
            )
            evolver = object.__new__(ParallelSkillEvolver)
            evolver.semantic_item_marker_format = "bracket"
            patch = SemanticPatch(
                reasoning="one",
                items=[SemanticPatchItem("SKILL.md", "add", "root", "retain")],
                changelog_entries=["one"],
                batch_index=1,
            )
            save_frozen_map(
                evolver,
                [patch],
                root / "shared-map",
                [{"instance_id": "train-a"}],
                batch_size=1,
            )
            result = preflight(
                method="semantic-reduce",
                m_core=m_core,
                memories=memories,
                batch_size=1,
                merge_batch_size=5,
                max_merge_levels=5,
                shared_map_dir=root / "shared-map",
            )
            self.assertEqual(0, result["network_requests"])
            self.assertEqual("reuse_frozen", result["shared_map_action"])
            self.assertEqual(1, result["shared_map_item_count"])


if __name__ == "__main__":
    unittest.main()
