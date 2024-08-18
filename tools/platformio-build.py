import sys
from os.path import isdir, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

FRAMEWORK_DIR = platform.get_package_dir("framework-nrf5sdk")
assert isdir(FRAMEWORK_DIR)

sdk_dir = join(FRAMEWORK_DIR, "sdk")
components_dir = join(sdk_dir, 'components')
lib_dir = join(components_dir, 'libraries')
nrfx_dir = join(sdk_dir, 'modules', 'nrfx')

mcu_long = board.get("build.mcu", "")  # e.g. NRF52810_XXAA
mcu_short = mcu_long.split('_', maxsplit=1)[0]  # e.g. NRF52810

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=["-std=gnu17"],

    CCFLAGS=[
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-mthumb",
        "-nostdlib",
        "--param",  "max-inline-insns-single=500"
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions",
        "-std=gnu++17",
        "-fno-threadsafe-statics"
    ],

    CPPDEFINES=[
        ("F_CPU", board.get("build.f_cpu")),
        "NRF5",
        "NRF52_SERIES" if "NRF52" in mcu_long.upper() else "NRF51",
        mcu_long.upper(),
        'NRF_DRV_UART_WITH_UARTE',
    ],

    LIBPATH=[
        join(sdk_dir, 'modules', 'nrfx', 'hal')
    ],

    # includes
    CPPPATH=[
        nrfx_dir,
        join(nrfx_dir, 'hal'),
        join(nrfx_dir, 'mdk'),
        join(nrfx_dir, 'drivers', 'include'),
        join(sdk_dir, 'integration', 'nrfx'),
        join(sdk_dir, 'integration', 'nrfx', 'legacy'),
        join(nrfx_dir, 'templates'),  # nrfx_log.h stub is here;
        # join(nrfx_dir, 'templates', mcu_short),  # nrfx_config.h examples are here
        # join(sdk_dir, 'config', mcu_short, 'config'),
        join(components_dir, 'boards'),
        # join(lib_dir, 'bsp'),
        # join(lib_dir, 'cli'),
        # join(lib_dir, 'timer'),
        join(lib_dir, 'log'),
        # join(lib_dir, 'button'),
        join(lib_dir, 'util'),
        # join(lib_dir, 'delay'),
        join(components_dir, 'toolchain', 'cmsis', 'include'),
        join(components_dir, 'drivers_nrf', 'nrf_soc_nosd'),
        join(env.subst("${PROJECT_INCLUDE_DIR}")),  # sdk_config.h should be here
    ],

    LINKFLAGS=[
        "-Os",
        "-Wl,--gc-sections",
        "-mthumb",
        "--specs=nano.specs",
        "--specs=nosys.specs",
        "-Wl,--check-sections",
        "-Wl,--unresolved-symbols=report-all",
        "-Wl,--warn-common",
        "-Wl,--warn-section-align"
    ],

    LIBSOURCE_DIRS=[lib_dir],

    LIBS=["m"]
)

if "BOARD" in env:
    env.Append(
        CCFLAGS=[
            "-mcpu=%s" % env.BoardConfig().get("build.cpu")
        ],
        LINKFLAGS=[
            "-mcpu=%s" % env.BoardConfig().get("build.cpu")
        ]
    )

# only nRF5283x and nRF52840 have FPUs
if any(mcu in board.get("build.mcu") for mcu in {'5283', '52840'}):
    env.Append(
        ASFLAGS=[
            "-mfloat-abi=hard",
            "-mfpu=fpv4-sp-d16",
        ],
        CCFLAGS=[
            "-mfloat-abi=hard",
            "-mfpu=fpv4-sp-d16"
        ],
        LINKFLAGS=[
            "-mfloat-abi=hard",
            "-mfpu=fpv4-sp-d16"
        ]
    )

if "build.usb_product" in env.BoardConfig():
    env.Append(
        CPPDEFINES=[
            "USBCON",
            "USE_TINYUSB",
            ("USB_VID", board.get("build.hwids")[0][0]),
            ("USB_PID", board.get("build.hwids")[0][1]),
            ("USB_PRODUCT", '\\"%s\\"' % board.get("build.usb_product", "").replace('"', "")),
            ("USB_MANUFACTURER", '\\"%s\\"' % board.get("vendor", "").replace('"', ""))
        ]
    )

env.Append(
    ASFLAGS=env.get("CCFLAGS", [])[:]
)

if not board.get("build.ldscript", ""):
    env.Replace(LDSCRIPT_PATH=board.get("build.arduino.ldscript", ""))

bootloader_opts = board.get("bootloaders", "")
bootloader_sel = env.GetProjectOption("board_bootloader", "")
ldscript = board.get("build.arduino.ldscript", "")

if bootloader_opts:
    if not bootloader_sel:
        sys.stderr.write("Error. Board type requires board_bootloader to be specified\n")
        env.Exit(1)

    if bootloader_sel not in bootloader_opts and bootloader_sel != "none":
        sys.stderr.write(
            "Error. Invalid board_bootloader selection. Options are: %s or none\n" %
            " ".join(k for k in bootloader_opts.keys()))
        env.Exit(1)

    if bootloader_sel == "adafruit":
        env.Replace(BOOTLOADERHEX=join(FRAMEWORK_DIR, "variants", board.get("build.variant", ""), "ada_bootloader.hex"))
        # Update the linker file for bootloader use and set a flag for the build.
        env.Append(CPPDEFINES=["USE_ADA_BL"])
        env.Replace(LDSCRIPT_PATH=ldscript[:-3] + "_adabl" + ldscript[-3:])
        board.update("upload.maximum_size", board.get("upload.maximum_size") - 53248)
        board.update("upload.maximum_ram_size", board.get("upload.maximum_ram_size") - 8)

libs = []

libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "sdk_components"),
        components_dir,
        [
            '+<boards>',
        ]
    ))
libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "sdk_nrfx"),
        sdk_dir,
        [
            '+<modules/nrfx/drivers/src>',
            '+<integration/nrfx/legacy>',
        ]
    ))

env.Prepend(LIBS=libs)
