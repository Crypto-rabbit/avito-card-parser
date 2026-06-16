import unittest

from avito_parser.parser import parse_card


class ParserTest(unittest.TestCase):
    def test_parse_basic_card_html(self):
        content = """
        <html>
          <body>
            <h1>Тестовый товар</h1>
            <div class="price-value">12 500 ₽</div>
            <div data-marker="seller-info/name">Иван</div>
            <div class="item-description">Описание товара</div>
            <script>
              window.__initialData__ = {"locationName": "Москва", "imagesCount": 3};
            </script>
          </body>
        </html>
        """

        card = parse_card("https://www.avito.ru/moskva/test_1234567890", content)

        self.assertEqual(card.item_id, "1234567890")
        self.assertEqual(card.title, "Тестовый товар")
        self.assertEqual(card.price, "12 500 ₽")
        self.assertEqual(card.location, "Москва")
        self.assertEqual(card.description, "Описание товара")
        self.assertEqual(card.images_count, "3")


if __name__ == "__main__":
    unittest.main()
