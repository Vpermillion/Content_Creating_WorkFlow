import unittest
from xml.etree import ElementTree
from whatif.anime_visuals import KINDS, storyboard
from whatif.media import diagram


class AnimeStoryboardTests(unittest.TestCase):
    def test_all_scene_types_are_valid_svg_and_escape_external_text(self):
        for index, kind in enumerate(sorted(KINDS)):
            scene = {"visual": kind, "label": "A < B & C"}
            svg = diagram(scene, index, len(KINDS), "A <script> & title")
            root = ElementTree.fromstring(svg)
            self.assertEqual(root.attrib["viewBox"], "0 0 720 1280")
            self.assertIn("ALTERNATE TIMELINE / FAN SCENARIO", svg)
            self.assertNotIn("<script>", svg)
            self.assertIn("&lt;", svg)

    def test_unknown_anime_kind_does_not_fall_back_to_unrelated_visual(self):
        with self.assertRaises(ValueError):
            storyboard({"visual": "anime-unrecognized", "label": "Test"}, 0, 1, "Test")


if __name__ == "__main__":
    unittest.main()
