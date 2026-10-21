# work

The private workspace. Everything here is git-ignored, and nothing here is
published.

| Path | What it holds |
|---|---|
| `pkg/` | the package and the files extracted from it |
| `extracted/` | the decrypted executable and the rebuilt ELF |
| `iso/` | the retail disc image |
| `analysis/` | the function catalogue, the prologue and call scans, the cross-game study |
| `bounds/` | the catalogue's measurements, the truth list, the evaluation |
| `gate/` | the body's scratch output and its receipts |
| `toolchain-src/` | the published toolchain sources of the SDK 1.9.0 generation |
| `ps3gcc-190/` | the build of that toolchain, and its log |
| `tools/` | the private helpers: the SELF decryption and the key extraction |
| `tools_pub/` | a copy of the published tools, for the measurements |

The rules are the same as everywhere else in the project: the workspace
holds the game-derived material, the repository holds the written result.
A lot directory is temporary; what matters is what the pull request says.

## The pipeline

1. **Read the package** (the published tool, no keys needed):

   ```sh
   python master/tools/pkg.py inspect "<package>.pkg"
   python master/tools/pkg.py extract  "<package>.pkg" --out pkg --only EBOOT.BIN --only PARAM.SFO
   ```

2. **Rebuild the executable** (private: the console key material stays
   here). The `.rap` file that belongs to the console is the one that
   came with the disc dump:

   ```sh
   python tools/eboot_decrypt.py pkg/USRDIR/EBOOT.BIN extracted/USRDIR/EBOOT.elf --rap "<licence>.rap"
   ```

3. **Read the executable** (the published tools):

   ```sh
   python master/tools/ppu_elf.py info     extracted/USRDIR/EBOOT.elf
   python master/tools/ppu_funcs.py catalogue extracted/USRDIR/EBOOT.elf --out analysis/catalogue.tsv
   python master/tools/ppu_bounds.py functions extracted/USRDIR/EBOOT.elf --out bounds/functions.tsv
   python master/tools/ppu_stubs.py extracted/USRDIR/EBOOT.elf
   ```

4. **Build the compiler** (the published sources of the SDK 1.9.0
   generation, in a Debian jessie container):

   ```sh
   python ps3gcc-190/build-toolchain.ps1
   ```

5. **Try a body** (the compiler, in the container that built it):

   ```sh
   python gate/try_body.py gate/candidates/module_init_v1.c 0x10210 \
       --symbol sub_146AC=0x146AC --symbol sub_10200=0x10200
   ```

   The gate compiles the candidate, links it at the measured address,
   applies the SDK's TOC-adjusting call rule and compares every byte with
   the retail ones.
