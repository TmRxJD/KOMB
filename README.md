<head><meta name="google-site-verification" content="YTr2AYTpsxIQk7KIOlVTOfKr11dqkzZP-gOUiyhPU5s" />
<body>
<h1>KOMB: Klipper's Ultimate Brushing Macro</h1>

Welcome to KOMB, the Klipper Optimized Macro for Brushing! This versatile macro streamlines brushing sequences, tailor-made for both bed and gantry mounted brushes. Say goodbye to the hassle of adapting existing macros or creating new ones—now you can harness the full potential of your brush in three dimensions!

<h3>Features and Functionality</h3>

Flexible Movement: KOMB's default motion sweeps from bottom left corner to right, but you can effortlessly customize movement along various axes and directions. Even use it mid-print depending on your printer and brush placement.

Diverse Patterns: Currently supports diagonal and circular sweeps (requires gcode_arcs enabled), KOMB's repertoire will soon expand to include more patterns.

3 Dimensional Brushing: Take advantage of the entire area and depth possible of your brush to ensure a cleaner nozzle with more consistent performance, you can be rest assured your nozzle will be clean every time. Nozzle can lower into the brush step by step to allow more nozzle surface area to reach the brush.

<h4>Adjustable Brush Parameters: Tweak variables for precise control</h4>
* Specify your brush location in (X, Y, Z), as well as the size and depth in millimeters <br>
* Step size: Distance between diagonal or circular strokes <br>
* Z-step: Descend after each iteration when using repeat. Set to 0 to disable. <br>
* Offset: Allows you to start and end movements outside the bounds of the brush, or to stay more confined within use a negative value for this <br>
* Repeat count: Specify how many times you want the pattern to iterate <br>
* Reverse: Enable to repeat the pattern back to the start in reverse before next repetition. If disabled nozzle will travel straight back to start after pattern <br>
* Start on Opposite and/or Adjacent side: If opposite side is enabled, nozzle will move from right to left. If adjacent is enabled, nozzle will move along the opposite axis and start on the bottom moving up. If both opposite and adjacent are enabled, nozzle will move from top to bottom. <br>
* Variable Speed: Specify speed in mm/s and increase or decrease the speed with each repitition. Also can control travel speed to brush <br>
* Patterns: Pick between different brushing patters, currently diagonals and circles are supported. (If you still wish to use a classic horizontal pattern you can, just set the brush size on the opposite axis to 0. If you still want it to be able to step set the angle to 0) <br>
* Angle: specify the angle of the diagonal strokes when using pattern 1, default recommended angle is 45 <br>
* Auto Heat: Enable and specify a minimum temperature to allow brushing at and automatically preheat to this temp before brushing <br>
* Auto Home: Automatically home printhead if needed. Will only home if not already. <br>
* Retraction: Configure retraction before, during, and after brushing. <br>
* Z Hop: Specify a height to raise nozzle to before moving to brush location and then lowering. Set to 0 to disable.
* Verbose Feedback: Enable verbose console output for comprehensive insights into the brushing process, including axis values, calculations, and positioning points. <br>

<h3>KOMB's Distinctiveness</h3>

KOMB is designed to seamlessly adapt to diverse printer setups, accommodating varying brush sizes and locations. Unlike traditional macros which brute-force your nozzle to move to specific locations, KOMB generates an entire sequence of coordinates based on your variables, preemptively adjusted to stay within printer limits. This proactive approach nearly eliminates the risk of errors to ensure successful brushing regardless of user error. Any generated points exceeding the printer's boundaries are automatically adjusted to be within, ensuring smooth execution. Once the list is instantly generated, KOMB guides the nozzle through the predetermined coordinates with ease.

<h3>Getting Started with KOMB</h3>

Ensure Klipper firmware is installed on your 3D printer.

Integrate the provided KOMB macro code into your Klipper configuration file (usually printer.cfg) or where your macros are stored.

Specify variables in the _KOMB_Variables section to match your brushing requirements.

Determine exact XY brush position via the printer's UI. Start from the bottom left corner, adjusting down to 0.1mm accuracy if you desire.

Measure brush size or calculate it by moving to the upper right corner and subtracting the lower left position from the upper right on both X and Y axes.
Repeat a similar process for the Z position, considering the option to lower the nozzle incrementally with each iteration (z_step).

Save the configuration file and reload Klipper to apply changes.

Execute KOMB in the console, via a UI macro button, or add "KOMB" to your start print macro. Ensure variables are configured accurately before execution.

Monitor progress through the console output when verbose output is enabled.

Enjoy Enhanced Brushing with KOMB!

<h4>Important Notes</h4>

This macro is designed to work with a range of variables and parameters. Make sure to adjust them according to your printer's specifications and your brushing needs. Make sure you understand what each variable does and how to use it.

Since this macro involves moving the printer's nozzle, exercise caution to avoid any collisions during the brushing process and ensure all values are correct. It is recommended to test the macro at a low speed above the brush before lowering it into position.

Be sure to check back in the future for updates and more patterns!

KOMB is a work in progress, and not all variable combinations have been thoroughly tested. Your feedback and contributions to improve the macro are highly appreciated.

If you encounter any issues, have suggestions for improvements, or wish to contribute to the development of KOMB, please feel free to message me, open an issue or submit a pull request on the GitHub repository. 

Happy KOMBing!
