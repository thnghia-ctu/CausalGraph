import unittest

from src.normalization.factor_parser import FactorParser


class FactorParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = FactorParser()

    def test_state_before_factor_core(self) -> None:
        result = self.parser.parse("giảm chi_phí_sản_xuất")

        self.assertEqual(result.factor_core, "chi phí sản xuất")
        self.assertEqual(result.state, "DECREASE")

    def test_state_after_factor_core(self) -> None:
        result = self.parser.parse("hạ_tầng mạng còn hạn_chế")

        self.assertEqual(result.factor_core, "hạ tầng mạng")
        self.assertEqual(result.state, "LIMITED")

    def test_state_between_subject_and_factor_core(self) -> None:
        result = self.parser.parse("nông_dân thiếu kỹ_năng số")

        self.assertEqual(result.factor_core, "kỹ năng số")
        self.assertEqual(result.state, "LACK")

    def test_factor_without_state(self) -> None:
        result = self.parser.parse("chất_lượng sản_phẩm")

        self.assertEqual(result.factor_core, "chất lượng sản phẩm")
        self.assertIsNone(result.state)


if __name__ == "__main__":
    unittest.main()
