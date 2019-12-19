#!/usr/bin/env python3

import argparse
import PIL.Image
import random

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






def run_arguments(options, force, file_in, file_out):
    raise NotImplementedError()


def build_parser(progname):
    parser = argparse.ArgumentParser(
        prog=progname, description="Make an image very trippy.")
    parser.add_argument('--options', default='{}', help='Options-dict in JSON')  # FIXME documentation?
    parser.add_argument('-f', '--force', action='store_true', help='Overwrite output file if exists')
    parser.add_argument('file_in', help='Input file, must be readable')
    parser.add_argument('file_out', help='Output file, must not exist')
    return parser


def run_argv(argv):
    import json
    parser = build_parser(argv[0])
    args = parser.parse_args(argv[1:])
    
    run_arguments(args.options, args.force, args.file_in, args.file_out)


if __name__ == '__main__':
    import sys
    run_argv(sys.argv)
