"""Pruebas públicas de ejemplo ampliadas con casos de prueba adicionales.

Pruebas: python3 -m unittest -v test_p1
"""

import re
import unittest

import regular_expressions as solution


class TestP1(unittest.TestCase):
    def check_language(self, pattern, valid, invalid):
        for expected, cases in ((True, valid), (False, invalid)):
            for text in cases:
                with self.subTest(text=text, expected=expected):
                    self.assertEqual(re.fullmatch(pattern, text) is not None, expected)

    def check_groups(self, pattern, text, expected):
        match = re.fullmatch(pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.groups(), expected)

    def test_exercise_0(self):
        self.check_language(solution.RE0, ["a", "abba"], ["", "ba"])

    def test_exercise_1(self):
        self.check_language(solution.RE1,
                            ["0", "10", "000", "1010101", "1110", "00000", "101010"],
                            ["", "1", "00", "010", "10a", "0000", "001"])

    def test_exercise_2(self):
        self.check_language(solution.RE2,
                            ["", "0", "1", "00100", "10101", "000", "10"],
                            ["11", "0110", "1011", "102", "110", "01011"])

    def test_exercise_3(self):
        self.check_language(solution.RE3,
                            ["0", "-12", "+3,14", "42,00", "-0,50", "-0", "100,55"],
                            ["00", "012,30", "3,", "3,1", "3,141", "3.14", "+01", "5,9"])

    def test_exercise_4(self):
        self.check_language(solution.RE4,
                            ["ana_lopez.txt", "datos/luis_gil.csv", "a_b.csv", "datos/a_b.txt", "juan_perez.csv"],
                            ["Ana_lopez.txt", "ana__lopez.txt", "ana_lopez.pdf",
                             "datos/ana_lopezXcsv", "otros/ana_lopez.csv", "datos/juan.txt", "datos/luis_gil.pdf"])

    def test_exercise_5(self):
        self.check_language(solution.RE5,
                            ["00:00:00", "09:07:05", "23:59:59", "12:30:45", "23:00:00"],
                            ["24:00:00", "12:60:00", "12:00:60", "9:07:05", "09:07", "25:00:00", "12:61:00"])
        self.check_groups(solution.RE5, "09:07:05", ("09", "07", "05"))
        self.check_groups(solution.RE5, "23:59:59", ("23", "59", "59"))

    def test_exercise_6(self):
        self.check_language(solution.RE6,
                            ["rgb(0,0,0)", "rgb(255,128,7)", "rgb(10,20,255)", "rgb(1,1,1)", "rgb(250,250,250)"],
                            ["rgb(256,0,0)", "rgb(01,2,3)", "rgb(-1,2,3)",
                             "rgb(1, 2,3)", "RGB(1,2,3)", "rgb(1,2,3,4)", "rgb(0,0,256)", "rgb(255,255,255,1)"])
        self.check_groups(solution.RE6, "rgb(255,128,7)", ("255", "128", "7"))

    def test_exercise_7(self):
        cases = [("uno   dos\ttres", "uno dos tres"),
                 ("  hola\t ", " hola "), ("a\n\t b", "a\n b"),
                 ("sin_cambios", "sin_cambios"), ("", ""),
                 ("\t\t", " "), ("palabra", "palabra"),
                 ("  inicio", " inicio"), ("fin  ", "fin ")]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(re.sub(solution.RE7, solution.SUB7, text), expected)

    def test_exercise_8(self):
        cases = [("lopez, ana", "ana lopez"), ("gil, luis", "luis gil"),
                 ("lopez,ana", "lopez,ana"), ("lopez,  ana", "lopez,  ana"),
                 ("x lopez, ana", "x lopez, ana"), ("lopez, ana\n", "lopez, ana\n"),
                 ("martin, juan", "juan martin"), ("gomez, eva", "eva gomez"),
                 ("martin, juan extra", "martin, juan extra"), ("123, ana", "123, ana")]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(re.sub(solution.RE8, solution.SUB8, text), expected)
        self.check_groups(solution.RE8, "lopez, ana", ("lopez", "ana"))


if __name__ == "__main__":
    unittest.main()