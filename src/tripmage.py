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
# * 'fn': function (x: float, y: float, w: int, h: int, ctx) -> (x: float, y: float), for the actual mapping
REGISTRY_INTERPOLATION = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (col_ul, col_ur, col_bl, col_br, x_frac: float, y_frac: float, ctx) -> col, for the actual mapping
#   (where `col` is a `Color` instance, and `x_frac` and `y_frac` are < 1.)
REGISTRY_COLORSPACE = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'rgb_to_col': function (r: int, g: int, b: int, ctx) -> col, for the "forwards" mapping
# * 'col_to_rgb': function (col) -> (r: int, g: int, b: int, ctx), for the "backwards" mapping
REGISTRY_COMPONENTS = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (x: int, y: int, w: int, h: int, ctx) -> (col, col, col), for the actual mapping
#   the returned colors must be unit-length and orthogonal.
REGISTRY_DISTORTION = dict()
# Registrees must define:
# * 'type': str, for easier debugging
# * 'fn': function (x: int, y: int, w: int, h: int, ctx) -> (float, float), for the actual mapping
#   Must return *relative* coordinates.  So the identity transform would be implememented by `return (0.0, 0.0)`


# Basically a `Vector3D`.
class Color:
    def __init__(self, abc):
        assert len(abc) == 3
        self.abc = abc

    @staticmethod
    def zero():
        return Color([0.0, 0.0, 0.0])

    @staticmethod
    def make_random_unit(rng):
        while True:
            col = Color([rng.gauss(0, 1) for _ in range(3)])
            length = col.vec_length()
            if length > 1e-2:
                return col.scale(1 / length)


    def copy(self):
        return Color(list(self.abc))  # Just to make sure

    def vec_length(self):
        return math.sqrt(sum(x ** 2 for x in self.abc))

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

    def pointwise_prod(self, rhs):
        return Color([(x * y) for x, y in zip(self.abc, rhs.abc)])

    def scalar_prod(self, rhs):
        return sum(self.pointwise_prod(rhs).abc)

    def cross_prod(self, rhs):
        a1, b1, c1 = self.abc
        a2, b2, c2 = rhs.abc
        return Color((b1 * c2 - c1 * b2, c1 * a2 - a1 * c2, a1 * b2 - b1 * a2))

    def __repr__(self):
        return '<Color {} at 0x{:016x}>'.format(self.abc, id(self))



def _register(registry, key, **kwargs):
    kwargs['type'] = key
    registry[key] = kwargs


def border_snap(x, y, w, h, ctx):
    x = min(max(0, x), w - 1)
    y = min(max(0, y), h - 1)
    return (x, y)


_register(REGISTRY_BORDER, 'snap', fn=border_snap)


def interpolate_nearest_neighbor(col_ul, col_ur, col_bl, col_br, x_frac, y_frac, ctx):
    assert 0 <= x_frac <= 1
    assert 0 <= y_frac <= 1
    return [[col_ul, col_ur], [col_bl, col_br]][y_frac >= 0.5][x_frac >= 0.5]


_register(REGISTRY_INTERPOLATION, 'nearest_neighbor', fn=interpolate_nearest_neighbor)


def color_projgamma_rgb2col(r, g, b, ctx):
    # First, scale down to the intervals [0.0, 1.0] and apply gamma-correction.
    # Then, rescale to the intervals [-1.0, +1.0].
    col = Color([(c / 255) ** ctx['gamma'] * 2 - 1 for c in [r, g, b]])
    # Next, find something that lies on the outside.
    max_component = max(abs(c) for c in col.abc)
    # Finally, reshape the cube into a sphere, by rescaling along each line individually:
    if max_component < 1e-4:
        # Eh, close enough, won't matter anyway.
        return col
    # Project `col` onto nearest cube face:
    #     col.scale(1 / max_component)
    # The length of that vector:
    #     col.vec_length() / max_component
    # Scaling *down* by that factor:
    return col.scale(max_component / col.vec_length())


def color_projgamma_col2rgb(col, ctx):
    # First,m undo the projection (see above):
    max_component = max(abs(c) for c in col.abc)
    if max_component >= 1e-4:
        col = col.scale(col.vec_length() / max_component)
    # Then go back to the intervals [0.0, 1.0], undo gamma-correction, and scale up to [0, 255].
    unitcube_rgb = [c / 2 + 0.5 for c in col.abc]
    assert all(-1e-6 < c < 1 + 1e-6 for c in unitcube_rgb), (col, unitcube_rgb)
    rgb = [min(max(0.0, c), 1.0) ** (1 / ctx['gamma']) * 255 for c in unitcube_rgb]
    # Finally, round and clip:
    try:
        return [min(max(0, round(c)), 255) for c in rgb]
    except BaseException as e:
        print(col.abc, rgb, [type(c) for c in rgb])
        raise e


_register(REGISTRY_COLORSPACE, 'projected_gammacorrected', gamma=2.4,
          rgb_to_col=color_projgamma_rgb2col,
          col_to_rgb=color_projgamma_col2rgb)


def components_staticrandom(x, y, w, h, ctx):
    ['ignore', x, y, w, h]
    if '_cache' not in ctx:
        rng = random.Random('components_staticrandom|' + ctx['seed'])
        c1 = Color.make_random_unit(rng)
        c3_dir = Color.make_random_unit(rng)
        # Scalar product is |v1| * |v2| * cos(angle).
        # We know |v1| = |v2| = 1, so we can immediately aregue about the angle.
        # We eventually want orthogonal vectors, so we can just restart until
        # we hit an angle of at least 20°, so we can compare against
        # cos(20°) = `math.cos(2 * math.pi/18)` >= 0.939.
        # So if it's smaller than 0.939, then the angle is "far" larger than 20°.
        # (In fact, at least 20.115°.)
        while c1.scalar_prod(c3_dir) < 0.984:
            c3_dir = Color.make_random_unit(rng)
        # The rest is easy:
        c2 = c1.cross_prod(c3_dir)
        c2 = c2.scale(1 / c2.vec_length())
        c3 = c1.cross_prod(c2)
        c3 = c3.scale(1 / c3.vec_length())
        ctx['_cache'] = [c1, c2, c3]
        for c in [c1, c2, c3]:
            assert -1e-6 < c.vec_length() - 1 < 1e-6, [c1, c3_dir, c2, c3]
    return tuple(c.copy() for c in ctx['_cache'])


_register(REGISTRY_COMPONENTS, 'static_random', fn=components_staticrandom)


def distortion_staticrandom(x, y, w, h, ctx):
    ['ignore', x, y, w, h]
    if '_cache' not in ctx:
        rng = random.Random('distortion_staticrandom|' + ctx['seed'])
        if ctx['scale_type'] == 'rel':
            magn_x = w * ctx['scale_x']
            magn_y = h * ctx['scale_y']
        elif ctx['scale_type'] == 'abs':
            magn_x = ctx['scale_x']
            magn_y = ctx['scale_y']
        else:
            raise ValueError('Unknown scale_type', ctx['scale_type'])
        x_offset = rng.uniform(-magn_x, magn_x)
        y_offset = rng.uniform(-magn_y, magn_y)
        ctx['_cache'] = [x_offset, y_offset]
    return list(ctx['_cache'])  # Copy


_register(REGISTRY_DISTORTION, 'static_random', fn=distortion_staticrandom,
          scale_type='rel', scale_x=0.05, scale_y=0.05)


def plug_call(options, entry, fn, *args, **kwargs):
    # It is *probably* possible to default `fn` to `'fn'`, but I really don't
    # want to fuck around too much with syntax-quirks like that.
    ctx = options[entry]
    assert isinstance(ctx, dict), (options, 'THE PROBLEM IS WITH KEY', entry, ctx)
    return ctx[fn](*args, **kwargs, ctx=ctx)


def read_rgb(img, x, y):
    raw = img.getpixel((x, y))
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
    assert 0 <= x < img_w
    assert 0 <= y < img_h
    xs = [math.floor(x), min(img_w - 1, math.ceil(x))]
    ys = [math.floor(y), min(img_h - 1, math.ceil(y))]
    cols = [read_rgb(img, x_int, y_int) for x_int in xs for y_int in ys]
    return plug_call(popopts, 'interpolation', 'fn', *cols, x - xs[0], y - ys[0])


def project_col(raw_col, component):
    assert -1e-6 < component.vec_length() - 1 < 1e-6, component
    assert -1 <= raw_col.vec_length() - 1 < 1e-6, raw_col
    return component.scale(raw_col.scalar_prod(component))


def run_options(img, popopts):
    data = []
    img_w, img_h = img.size
    dist_keys = ['distortion_{}'.format(i) for i in range(1, 3 + 1)]
    for dst_y in range(-popopts['margins']['top'], img_h + popopts['margins']['bottom']):
        for dst_x in range(-popopts['margins']['left'], img_w + popopts['margins']['right']):
            # Determine from where we should read the data:
            dist_vecs = [plug_call(popopts, dist_key, 'fn', dst_x, dst_y, img_w, img_h) for dist_key in dist_keys]
            source_locs = [plug_call(popopts, 'border', 'fn', dst_x - dist_x, dst_y - dist_y, img_w, img_h) for dist_x, dist_y in dist_vecs]

            # Make the data usable:
            source_rgbs = [compute_rgb(img, src_x, src_y, popopts) for src_x, src_y in source_locs]
            source_cols = [plug_call(popopts, 'colorspace', 'rgb_to_col', *rgb) for rgb in source_rgbs]

            # Determine which components to use at this point:
            component_vecs = plug_call(popopts, 'components', 'fn', dst_x, dst_y, img_w, img_h)

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
            result_rgb = plug_call(popopts, 'colorspace', 'col_to_rgb', result_col)
            data.append(tuple(result_rgb))

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
        'interpolation': REGISTRY_INTERPOLATION,
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
    print('Got options {}'.format(options))
    options = json.loads(options)
    populated_options = populate_options(options)

    if not force and os.path.exists(file_out):
        print('Output file {} already exists, aborting.  Use "-f" to overwrite.'.format(file_out), file=sys.stderr)
        exit(1)
    img = PIL.Image.open(file_in)

    result_img = run_options(img, populated_options)

    if verbose:
        def reprify(thing):
            if isinstance(thing, (str, int, float)):
                return thing
            elif isinstance(thing, dict):
                return {reprify(k): reprify(v) for k, v in thing.items()}
            else:
                return repr(thing)
        print(json.dumps(reprify(populated_options), indent=1, sort_keys=True))

    result_img.save(file_out)


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
