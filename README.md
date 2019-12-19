# tripmage

> A trippy image filter, depending on color space conversions.

This is based on a fun idea I had about color space re-assembly.

FIXME: Insert example, showing before/after.

## Table of Contents

- [Usage](#usage)
- [Background](#background)
- [Performance](#performance)
- [TODOs](#todos)
- [NOTDOs](#notdos)
- [Contribute](#contribute)

## Usage

Simple example:

```
FIXME
```

Can be made completely deterministic:

```
FIXME
```

Full help / "documentation":

```
$ ./tripmage.py --help
FIXME: Lots of options, I guess
```

## Background

The inspiration came when I saw the usual effect of "image with RGB channels separated and shifted against each other slighty".

I thought to myself "Why always RGB?"
Well, because that's easy to implement.
But that's actually the only reason:
All you need is a 3-dimensional colorspace, and this operation is well-defined.
And with other, arbitrary color spaces, it looks way cooler!

Next is the shift itself: Why is it always just three independent, constant vectors?
Well, because that's easy to implement.
But that's actually the only reason:
All you need is a distortion function (i.e. 2d-to-2d, somewhat continuous,
ideally Lipschitz bounded because it would be too distorted otherwise).
And with arbitrarily wacky distortions, it looks way trippier!

## Performance

FIXME

Probably shit, that's why I'll first write it in Python, then in Rust, I guess.

## TODOs

* Everything

## NOTDOs

* Not sure yet
* Does this need an install option?  [File a bug](https://github.com/BenWiederhake/tripmage/issues/new) if you think so.

## Contribute

Feel free to dive in! [Open an issue](https://github.com/BenWiederhake/tripmage/issues/new) or submit PRs.
