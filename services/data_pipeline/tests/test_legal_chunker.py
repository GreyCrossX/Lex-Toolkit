import unittest

import tiktoken

from services.data_pipeline.legal_chunker import (
    ArticleUnit,
    chunk_text_by_tokens,
    split_article_into_units,
)


class DummyArt:
    def __init__(self, number: str, text: str):
        self.number = number
        self.heading = None
        self.text = text


class SplitArticleIntoUnitsTests(unittest.TestCase):
    def test_simple_lead_paragraphs(self) -> None:
        text = (
            "Esta ley tiene por objeto establecer las bases de X.\n\n"
            "Para los efectos de esta ley, se entenderá por Y..."
        )
        art = DummyArt("1", text)
        units = split_article_into_units(art)

        self.assertEqual(len(units), 2)
        self.assertEqual(
            [(unit.kind, unit.fraction_label, unit.paragraph_index) for unit in units],
            [
                ("lead_paragraph", None, 1),
                ("lead_paragraph", None, 2),
            ],
        )
        self.assertTrue(units[0].text.startswith("Esta ley tiene"))
        self.assertTrue(units[1].text.startswith("Para los efectos"))

    def test_fractions_with_multiple_paragraphs(self) -> None:
        text = (
            "Las autoridades de la Ciudad de México deberán:\n\n"
            "I. Proteger el medio ambiente.\n\n"
            "II. Promover la participación ciudadana.\n\n"
            "En el caso de la fracción II:\n\n"
            "a) Podrán expedir convocatorias;\n\n"
            "b) Podrán celebrar convenios.\n\n"
            "III.- Garantizar el acceso a la información."
        )
        art = DummyArt("27", text)
        units = split_article_into_units(art)

        kinds = [(u.kind, u.fraction_label, u.paragraph_index) for u in units]
        self.assertEqual(
            kinds,
            [
                ("lead_paragraph", None, 1),
                ("fraction_paragraph", "I", 1),
                ("fraction_paragraph", "II", 1),
                ("fraction_paragraph", "II", 2),
                ("fraction_paragraph", "II", 3),
                ("fraction_paragraph", "II", 4),
                ("fraction_paragraph", "III", 1),
            ],
        )
        self.assertTrue(units[1].text.startswith("Proteger"))
        self.assertTrue(units[-1].text.startswith("Garantizar"))

    def test_chunk_text_by_tokens_overlaps(self) -> None:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as exc:
            self.skipTest(f"Tokenizer unavailable offline: {exc}")
        text = "Uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince."
        chunks = chunk_text_by_tokens(
            text,
            encoding,
            max_tokens=8,
            overlap_tokens=2,
        )
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertTrue(chunk.strip())


if __name__ == "__main__":
    unittest.main()
