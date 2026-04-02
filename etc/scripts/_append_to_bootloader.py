#!/usr/bin/env python3
"""Appends a bundled single-file Python distribution of Skybrush Studio for
Blender to the end of the bootloader executable (compiled separately in the
sbstudio-bootloader project) and produces the final executable that can be
distributed. The final executable invokes Blender and pipes the code of the
plugin into it so it does not mess up the Blender installation of the user.

This script is called from create_blender_dist.sh; in most cases you should
not need to call it directly.
"""

import sys
from argparse import ArgumentParser
from pathlib import Path
from struct import pack
from zlib import compress

MAGIC_MASK = 0x5B
"""XOR mask to use in the generated executable"""

MAGIC_TRAILER = b"\x5b\x57\x00\xd1\x01"
"""Magic trailer in the bootloader that is used to identify that the payload is
already appended"""


def mask_bytes(data: bytes, mask: int = MAGIC_MASK) -> bytes:
    return bytes(b ^ MAGIC_MASK for b in data)


def create_executable(bundle, bootloader, fp):
    with open(bootloader, "rb") as bootloader_fp:
        fp.write(bootloader_fp.read())

    with open(bundle, "rb") as bundle_fp:
        bundle = bundle_fp.read()

    bundle = compress(bundle, level=9)
    fp.write(mask_bytes(bundle))
    fp.write(mask_bytes(pack("!L", len(bundle))))
    fp.write(MAGIC_TRAILER)


def main():
    parser = ArgumentParser(description=sys.modules[__name__].__doc__)
    parser.add_argument(
        "--bootloader-dir",
        metavar="DIR",
        help="directory that contains the bootloader executables for the supported platforms",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        help="path of the folder to save the generated executables to",
        default=".",
    )
    parser.add_argument(
        "--platforms",
        metavar="PLATFORM1,PLATFORM2,...",
        help="comma-separated list of platforms to compile the final executable for",
        default="macos,linux,win64",
    )
    parser.add_argument(
        "bundle",
        metavar="FILENAME",
        help="name of the single-file Python bundle to attach to the bootloader",
        nargs=1,
    )
    args = parser.parse_args()

    args.platforms = [plat.strip().lower() for plat in args.platforms.split(",")]
    args.bootloader_dir = Path(args.bootloader_dir)
    args.output_dir = Path(args.output_dir)
    bundle = Path(args.bundle[0])

    if not args.bootloader_dir.is_dir():
        parser.error("Bootloader directory does not exist")

    if not bundle.is_file():
        parser.error("Python bundle does not exist or is not a single file")

    bootloaders = {}
    for plat in args.platforms:
        candidates = [f"sbstudio-bootloader-{plat}", f"sbstudio-bootloader-{plat}.exe"]
        for candidate in candidates:
            bootloader = args.bootloader_dir / candidate
            if bootloader.is_file():
                bootloaders[plat] = bootloader.resolve()
                break
        else:
            parser.error(
                f"No bootloader found for platform {plat!r} in {args.bootloader_dir}"
            )

    for plat, bootloader in bootloaders.items():
        output_filename = args.output_dir / f"{bundle.stem}-{plat}{bootloader.suffix}"
        with open(output_filename, "wb") as fp:
            create_executable(bundle, bootloader, fp)
        output_filename.chmod(0o755)


if __name__ == "__main__":
    sys.exit(main())
