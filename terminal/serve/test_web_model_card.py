"""The Monitor's Model card must not set the height of the gauge row (W1174).

Upstream PR #4968 put a block of text -- the model id and five session averages -- in the same
auto-fit grid as the sparklines, one 1fr track wide.  A 46-character id ("qwen3.8-flash-next-
ud-q4_k_xl-abliterated-v2") then broke after "q4_k_xl-", and the five rows it carries made the
whole row taller than any gauge needed, so the eight gauges sat in empty card.

No browser runs in this repo, so this checks the declarations that keep the card in line rather
than the pixels.  It is a shape test: it cannot say the page looks right, only that the three
rules cannot be dropped without a red.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = open(os.path.join(HERE, "web", "app.css"), encoding="utf-8").read()
JS = open(os.path.join(HERE, "web", "app.js"), encoding="utf-8").read()

WIDE = re.search(r"@media \(min-width: 1200px\) \{(.*?)\n\}", CSS, re.S)
NARROW = re.search(r"@media \(max-width: 760px\) \{(.*?)\n\}", CSS, re.S)


def block(selector):
    m = re.search(re.escape(selector) + r" \{[^}]*\}", CSS)
    return m.group(0) if m else ""


class ModelCard(unittest.TestCase):
    def test_the_card_is_still_the_first_metric(self):
        """It is upstream's card; the layout fix must not become a quiet removal."""
        self.assertIn('{key: "model", label: "Model"', JS)
        self.assertLess(JS.index('{key: "model"'), JS.index('{key: "speed"'))

    def test_wide_screens_give_it_two_tracks(self):
        self.assertTrue(WIDE, "the wide-screen rule is missing")
        self.assertIn(".model-card { grid-column: span 2; }", WIDE.group(1))

    def test_the_name_stays_on_one_line(self):
        b = block(".model-card__name")
        self.assertIn("white-space: nowrap", b)
        self.assertIn("text-overflow: ellipsis", b)
        self.assertNotIn("overflow-wrap: anywhere", b)

    def test_the_five_averages_fit_two_columns(self):
        self.assertIn("grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 1fr)", WIDE.group(1))
        # the fifth pair (Since . N requests) keeps the full width instead of a dangling half row
        self.assertIn(".model-card__facts > :nth-last-child(-n + 2) { grid-column: span 2; }", WIDE.group(1))

    def test_narrow_screens_clamp_instead_of_overflowing(self):
        self.assertTrue(NARROW, "the narrow-screen rule is missing")
        self.assertIn("-webkit-line-clamp: 2", NARROW.group(1))
        self.assertIn("grid-template-columns: auto minmax(0, 1fr)", NARROW.group(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
