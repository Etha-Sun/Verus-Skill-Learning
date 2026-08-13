from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "semantic_v4" / "verus-proof-repair" / "references"


class SkillMarkdownRenderingTests(unittest.TestCase):
    def test_card_anchors_are_separated_from_markdown_headings(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(REFERENCES.glob("*.md"))
        )
        anchors = re.findall(r'<a id="(verus-global-\d{3})"></a>', combined)
        rendered_pairs = re.findall(
            r'<a id="(verus-global-\d{3})"></a>\n\n'
            r'## (verus_global_\d{3}) — ',
            combined,
        )
        self.assertEqual(len(anchors), 88)
        self.assertEqual(len(rendered_pairs), 88)
        for anchor, heading in rendered_pairs:
            self.assertEqual(anchor.replace("-", "_"), heading)


if __name__ == "__main__":
    unittest.main()
