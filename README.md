A PlatformIO Framework intended to compile nRF5 SDK programs
 unmodified or with minimal modifications.


* sdk/components/libraries - only some are added as headers, to make some examples compile.
    "util", "delay", "cmsis", "bsp", "button"
* libraries - parts from SDK that you need to include in platformio.ini as "lib_deps"
    * freertos. Add FreeRTOSConfig to your project (example can be found in config folder)
