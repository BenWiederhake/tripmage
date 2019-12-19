#!/usr/bin/env python3

import argparse
import json
import os.path
import PIL.Image
import random
import sys

REGISTRY_BORDER = dict()
REGISTRY_BORDER_DEFAULT = 'constant'

REGISTRY_COLORSPACE = dict()
REGISTRY_COLORSPACE_DEFAULT = 'projected_alpha'

REGISTRY_COMPONENTS = dict()
REGISTRY_COMPONENTS_DEFAULT = 'constant'

REGISTRY_DISTORTION = dict()
REGISTRY_DISTORTION_DEFAULT = 'static_random'

REGISTRY_ALPHA = dict()
REGISTRY_ALPHA_DEFAULT = 'average'

# General:
    # * Margins (positive *and* negative)
    # * Border conditions: {constant, snap}
    # * Seed (also everywhere else)
# RGB → Sphere
    # * 'pre-alpha'
    # * method: {projection, ???}
# 2D-to-SO(3) function
    # * method: {constant, ???}
    # * its arguments
# 3 potentially separate 2D distortions
    # * method: {constant, ???}
    # * its arguments
# Alpha merging:
    # * method: {average, median, ???}
# Sphere → RGB
    # * 'post-alpha'
    # * method: {projection, ???}



def run_options(img, populated_options):
    raise NotImplementedError()


def populate_options(options):
    assert isinstance(options, dict), type(options)
    raise NotImplementedError()


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
