# Legal and distribution boundary

This repository publishes **independently authored** material only: written
C/C++ source, tools, research metadata and documentation.

## What this repository never contains

* The game package, disc image, retail executable, extracted modules,
  instruction listings, disassembly or any other game-derived byte.
* Game assets: models, textures, audio, video, fonts, levels.
* Console key material: `NP_KLIC_*`, `RAP_KEY`, the NPDRM key vault, a
  `.rap` licence file, a `klic`, or a console dump.
* Proprietary toolchains, SDK sources, headers or samples.
* Leaked or NDA material of any kind.

The tools in `tools/` read a package and a decrypted executable from a path
the contributor chooses; they never ship one.

## What a contributor needs

Your own lawful copy of the game, and the licence file that belongs to your
own console. Nothing of that travels to this repository: the local
workspace is private and git-ignored, and the results that are published are
the written reasoning, the measurements (addresses, sizes, hashes) and the
tools.

The same rule applies to the **toolchain**. A matching decompilation needs
the compiler that produced the retail bytes; the project does not ship one,
does not mirror one, does not describe how to obtain one, and does not
publish a proprietary toolchain, a confidential source package, an SDK
header or an SDK library. A contributor who has a licensed toolchain uses it
in their own workspace, exactly like the sibling PlayStation 2 projects do
with Sony's SN ProDG.

## Sourcing policy

The evidence standard is the same as the sibling Ratchet &amp; Clank
projects: your own disc and your own console are the evidence. Third-party
open-source tools may be studied, cited and re-implemented, with attribution
and their licences respected; the published tools here are written from the
documented container formats and from the public documentation of the
formats.

## Trademarks

Ratchet &amp; Clank is a trademark of Sony Interactive Entertainment. The game
was developed by Insomniac Games. This project is an unofficial fan work, not
affiliated with, authorised by or endorsed by either, and it hosts no game
content.

## Licence

The independently authored material in this repository is GPL-3.0; see
`LICENSE`. That licence covers the repository's own work only: it does not
cover the game, its assets, console key material or proprietary toolchains.
Contributions should be original or compatible with GPL-3.0, with attribution
where required.
