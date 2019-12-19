#!/usr/bin/env python3

import math
import tripmage
import unittest

class TestStringMethods(unittest.TestCase):
    def test_border_snap(self):
        for xywhab in [
                (-5, -5, 10, 10, 0, 0),
                (15, 15, 10, 10, 9, 9),
                (15, 15, 20, 10, 15, 9),
                (30, 30, 20, 40, 19, 30),
                (4, 2, 8, 7, 4, 2),
                ]:
            with self.subTest(xywhab=xywhab):
                x, y, w, h, a, b = xywhab
                self.assertEqual(tripmage.border_snap(x, y, w, h, None), (a, b))

    def test_interpolate_nearest_neighbor(self):
        for x_frac, y_frac, expect in [
                (0.00, 0.00, 'ul'),
                (0.10, 0.10, 'ul'),
                (0.40, 0.40, 'ul'),
                (0.45, 0.15, 'ul'),
                (0.51, 0.00, 'ur'),
                (0.51, 0.49, 'ur'),
                (0.49, 0.51, 'bl'),
                (0.00, 0.99, 'bl'),
                (0.99, 0.99, 'br'),
                ]:
            with self.subTest(x_frac=x_frac, y_frac=y_frac, expect=expect):
                self.assertEqual(tripmage.interpolate_nearest_neighbor('ul', 'ur', 'bl', 'br', x_frac, y_frac, None), expect)

    def test_color_projalpha_rgb2col(self):
        DELTA = 1e-8
        isqrt3 = 1 / math.sqrt(3)
        isqrt2 = 1 / math.sqrt(2)
        for rgbgcol in [
                (127.5, 127.5, 127.5, 1, 0, 0, 0),
                (255.0, 127.5, 127.5, 1, 1, 0, 0),
                (  0.0, 127.5, 127.5, 1, -1, 0, 0),
                (127.5, 255.0, 127.5, 1, 0, 1, 0),
                (127.5,   0.0, 127.5, 1, 0, -1, 0),
                (127.5, 127.5, 255.0, 1, 0, 0, 1),
                (127.5, 127.5,   0.0, 1, 0, 0, -1),
                (  0.0,   0.0,   0.0, 1, -isqrt3, -isqrt3, -isqrt3),
                (  0.0,   0.0,   0.0, 2, -isqrt3, -isqrt3, -isqrt3),
                (  0.0,   0.0,   0.0, 0.1, -isqrt3, -isqrt3, -isqrt3),
                (255.0, 255.0, 255.0, 1,  isqrt3,  isqrt3,  isqrt3),
                (255.0,   0.0,   0.0, 1,  isqrt3, -isqrt3, -isqrt3),
                (  0.0, 255.0,   0.0, 1, -isqrt3,  isqrt3, -isqrt3),
                (  0.0,   0.0, 255.0, 1, -isqrt3, -isqrt3,  isqrt3),
                (255.0, 127.5, 255.0, 1,  isqrt2,       0,  isqrt2),
                (127.5,   0.0, 255.0, 1,       0, -isqrt2,  isqrt2),
                (  0.0, 255.0, 127.5, 1, -isqrt2,  isqrt2,       0),
                ]:
            r, g, b, gamma, ce1, ce2, ce3 = rgbgcol
            ca1, ca2, ca3 = tripmage.color_projgamma_rgb2col(r, g, b, dict(gamma=gamma)).abc
            with self.subTest(rgbgcol=rgbgcol, actual=(ca1, ca2, ca3)):
                self.assertAlmostEqual(ca1, ce1, delta=DELTA)
                self.assertAlmostEqual(ca2, ce2, delta=DELTA)
                self.assertAlmostEqual(ca3, ce3, delta=DELTA)


    def test_color_projalpha_col2rgb(self):
        for rgbg in [
                (127, 127, 128, 1),
                (255, 128, 127, 1),
                (  0, 127, 127, 1),
                (128, 255, 127, 1),
                (127,   0, 128, 1),
                (128, 128, 255, 1),
                (127, 127,   0, 1),
                (  0,   0,   0, 1),
                (  0,   0,   0, 2),
                (  0,   0,   0, 0.1),
                (255, 255, 255, 1),
                (255,   0,   0, 1),
                (  0, 255,   0, 1),
                (  0,   0, 255, 1),
                (255, 128, 255, 1),
                (128,   0, 255, 1),
                (  0, 255, 128, 1),
                # Some random RGB values.  Generated via `tuple(round(random.random()*255)for _ in range(3))`:
                (228, 200, 255, 1),
                (228, 200, 255, 2),
                (228, 200, 255, 2.2),
                (228, 200, 255, 1.3),
                (228, 200, 255, 0.6),
                (252,  56,  58, 1),
                ( 51, 200,  91, 1),
                (206, 217,  62, 1),
                ]:
            r, g, b, gamma = rgbg
            col = tripmage.color_projgamma_rgb2col(r, g, b, dict(gamma=gamma))
            actual = tripmage.color_projgamma_col2rgb(col, dict(gamma=gamma))
            with self.subTest(rgbg=rgbg, col=col.abc, actual=actual):
                self.assertEqual(r, actual[0])
                self.assertEqual(g, actual[1])
                self.assertEqual(b, actual[2])

    def test_components_staticrandom(self):
        DELTA = 1e-6

        def flatten(vecs):
            return [c for vec in vecs for c in vec.abc]

        for seed in ['hello', 'world', 'how', 'are', 'you', 'today']:
            ctx = dict(seed=seed)
            with self.subTest(seed=seed, ctx=ctx):
                actual = tripmage.components_staticrandom(None, None, None, None, ctx)
                if seed == 'hello':
                    expected = [-0.4674090892109045, -0.8493668067334561, -0.24516274378959885, 0.39164765287163433, -0.44757070518681635, 0.8039232425167938, -0.7925533794787407, 0.2797436174034856, 0.5418511319530853]
                    self.assertEqual(flatten(actual), expected)
                self.assertEqual(flatten(actual), flatten(ctx['_cache']))
                self.assertEqual(flatten(actual), flatten(tripmage.components_staticrandom(None, None, None, None, ctx)))
                # Assert orthogonal and normed:
                self.assertAlmostEqual(actual[0].scalar_prod(actual[0]), 1.0, delta=DELTA)
                self.assertAlmostEqual(actual[0].scalar_prod(actual[1]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[0].scalar_prod(actual[2]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[1].scalar_prod(actual[0]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[1].scalar_prod(actual[1]), 1.0, delta=DELTA)
                self.assertAlmostEqual(actual[1].scalar_prod(actual[2]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[2].scalar_prod(actual[0]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[2].scalar_prod(actual[1]), 0.0, delta=DELTA)
                self.assertAlmostEqual(actual[2].scalar_prod(actual[2]), 1.0, delta=DELTA)


if __name__ == '__main__':
    unittest.main()
