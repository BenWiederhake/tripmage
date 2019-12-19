#!/usr/bin/env python3

import argparse
import json
import math
import os.path
import PIL.Image
import random
import sys

OPTIONS_DEFAULT = {
    'seed': 'asdf',
    'margins': {  # ← needs special handling as it is mutable
        'top': 0,
        'bottom': 0,
        'left': 0,
        'right': 0,
    },
    'border': 'snap',
    'interpolation': 'nearest_neighbor',  # TODO: Implement
    'colorspace': 'projected_gammacorrected',  # TODO: Implement
    'components': 'static_random',  # TODO: Implement
    # I know, a list to store the distortions would me more intuitive.
    # However, this way the defaulting is slightly easier.
    'distortion_1': 'static_random',  # TODO: Implement
    'distortion_2': 'static_random',
    'distortion_3': 'static_random',
}

REGISTRY_BORDER = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (x: float, y: float, w: int, h: int) -> (x: float, y: float), for the actual mapping
REGISTRY_INTERPOLATION = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (col_ul, col_ur, col_bl, col_br, x_frac: float, y_frac: float) -> col, for the actual mapping
#   (where `col` is a `Color` instance, and `x_frac` and `y_frac` are < 1.)
REGISTRY_COLORSPACE = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'rgb_to_col': function (r: int, g: int, b: int) -> col, for the "forwards" mapping
# * 'col_to_rgb': function (col) -> (r: int, g: int, b: int), for the "backwards" mapping
REGISTRY_COMPONENTS = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (x: int, y: int) -> (col, col, col), for the actual mapping
#   the returned colors must be unit-length and orthogonal.
REGISTRY_DISTORTION = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (x: int, y: int) -> (float, float), for the actual mapping


# Basically a `Vector3D`.
class Color:
    def __init__(self, abc):
        assert len(abc) == 3
        self.abc = abc

    @staticmethod
    def zero():
        return Color([0.0, 0.0, 0.0])

    def copy(self):
        return Color(list(self.abc))  # Just to make sure

    def vec_length(self):
        return sqrt(sum(x ** 2 for x in self.abc))

    def clip_length(self, max_length):
        actual_length = self.vec_length()
        if actual_length > max_length:
            return self.scale(max_length / actual_length)
        else:
            return self.copy()

    def scale(self, factor):
        return Color([x * factor for x in self.abc])

    def __add__(self, rhs):
        return Color([(x + y) for x, y in zip(self.abc, rhs.abc)])

    def __mul__(self, rhs):
        return Color([(x * y) for x, y in zip(self.abc, rhs.abc)])

    def scalar_prod(self, rhs):
        return sum(self * rhs)


def read_rgb(img, x, y):
    raw = img.getpixel(x, y)
    if len(raw) == 1:
        return raw * 3
    elif len(raw) == 3:
        return raw
    elif len(raw) == 4:
        return raw[:3]
    else:
        raise AssertionError('What kind of channelset is this?!', raw, img.mode, (x, y))


def compute_rgb(img, x: float, y: float, popopts):
    img_w, img_h = img.size
    assert 0 <= x <= img_w - 1
    assert 0 <= y <= img_h - 1
    xs = [math.floor(x), math.ceil(x)]
    ys = [math.floor(y), math.ceil(y)]
    cols = [read_rgb(img, x_int, y_int) for x in xs for y in ys]
    return popopts['interpolation']['fn'](*cols, x - xs[0], y - ys[0])


def project_col(raw_col, component):
    assert -1e-6 < component.vec_length() - 1 < 1e-6
    assert raw_col.vec_length() - 1 < 1e-6
    return sum((raw_col * component).abc)


def run_options(img, popopts):
    data = []
    img_w, img_h = img.size
    dist_keys = ['distortion_{}'.format(i) for i in range(1, 3 + 1)]
    for dst_y in range(-popopts['margins']['top'], img_h + popopts['margins']['bottom']):
        for dst_x in range(-popopts['margins']['left'], img_w + popopts['margins']['right']):
            # Determine from where we should read the data:
            source_locs_raw = [popopts[dist_key]['fn'](dst_x, dst_y) for dist_key in dist_keys]
            source_locs = [popopts['border']['fn'](src_x, src_y, img_w, img_h) for src_x, src_y in source_locs_raw]

            # Make the data usable:
            source_rgbs = [compute_rgb(img, src_x, src_y, popopts) for src_x, src_y in source_locs]
            source_cols = [popopts['colorspace']['rgb_to_col'](rgba[:3]) for rgba in source_rgbas]

            # Determine which components to use at this point:
            component_vecs = popopts['components']['fn'](dst_x, dst_y)

            # Project onto the components we're actually interested in:
            component_cols = [project_col(raw_col, component) for raw_col, component in zip(source_cols, component_vecs)]

            # Combine:
            result_col = sum(component_cols, Color.zero()).clip_length(1)
            # `clip_length` is necessary as we're doing a component analysis
            # of three *different* colors.  If all distortions were just identity,
            # i.e. no distortions at all, then no clipping would happen at all.
            # Therefore, clipping only happens when the involved values are extreme,
            # so clipping is basically the only reasonable method.
            # If you disagree, feel free to open up yet another 'registry'.

            # Aaand done:
            result_rgb = popopts['colorspace']['col_to_rgb'](result_col)
            data.append(result_rgb)

    result = PIL.Image.new(
        'RGB',
        (popopts['margins']['left']+ img_w + popopts['margins']['right'],
         popopts['margins']['top'] + img_h + popopts['margins']['bottom']))
    # From experience it's faster to write everything into a list first,
    # and then bulk-load it into the image.  I am aware that `putpixel` exists.
    # TODO: Benchmark whether this is actually the case?
    result.putdata(data)
    return result


def populate_options(raw_options):
    assert isinstance(raw_options, dict), type(raw_options)

    # Fill-in the default values:
    options = dict(OPTIONS_DEFAULT)
    options.update(raw_options)
    if 'margins' in raw_options:
        # Copy "manually", because the margins-dict is mutable:
        options['margins'] = dict(OPTIONS_DEFAULT['margins'])
        options['margins'].update(raw_options['margins'])

    # Expand all shortnames:
    registries = {
        'border': REGISTRY_BORDER,
        'colorspace': REGISTRY_COLORSPACE,
        'components': REGISTRY_COMPONENTS,
        'distortion_1': REGISTRY_DISTORTION,
        'distortion_2': REGISTRY_DISTORTION,
        'distortion_3': REGISTRY_DISTORTION,
    }
    for key, registry in registries.items():
        if isinstance(options[key], str):
            base = registry[options[key]].copy()
            options[key] = base
        elif isinstance(options[key], dict):
            base = registry[options[key]['type']].copy()
            base.update(options[key])
            options[key] = base
        else:
            raise AssertionError('value for option {} has unexpected type {} (expected str or dict)'.format(key, type(options[key])))

        if 'seed' not in options[key]:
            options[key]['seed'] = 'default {} seed from {}'.format(key, options['seed'])

    return options


def run_arguments(options, force, verbose, file_in, file_out):
    options = json.loads(options)
    populated_options = populate_options(options)
    if verbose:
        print(json.dumps(populate_options, sort_keys=True))

    if not force and os.path.exists(file_out):
        print('Output file {} already exists, aborting.  Use "-f" to overwrite.'.format(file_out), file=sys.stderr)
        exit(1)
    img = PIL.Image.open(file_in)

    run_options(img, populated_options)

    img.save(file_out)


def build_parser(progname):
    parser = argparse.ArgumentParser(
        prog=progname, description="Make an image very trippy.")
    parser.add_argument('--options', default='{}', help='Options-dict in JSON')  # FIXME documentation?
    parser.add_argument('-f', '--force', action='store_true', help='Overwrite output file if exists')
    parser.add_argument('-v', '--verbose', action='store_true', help='Report actual options-dict in JSON')
    parser.add_argument('file_in', help='Input file, must be readable')
    parser.add_argument('file_out', help='Output file, must not exist')
    return parser


def run_argv(argv):
    parser = build_parser(argv[0])
    args = parser.parse_args(argv[1:])
    
    run_arguments(args.options, args.force, args.verbose,
        args.file_in, args.file_out)


if __name__ == '__main__':
    import sys
    run_argv(sys.argv)
