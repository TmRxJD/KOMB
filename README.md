<h1>KOMB: The Klipper Optimized Macro for Brushing</h1>

Welcome to KOMB, the Klipper Optimized Macro for Brushing! This macro provides a versatile solution for controlling brushing sequences with various options, suitable for both bed and gantry mounted brushes. No longer will you have to mess with finding and adapting someone else's macro to work with your printer, or having to create a macro of your own, and enjoy making more use of the full area of your brush by allowing brushing in 3 dimensions. 

<h3>Features and Behavior</h3>

Customizable Movement: KOMB's default behavior is to move from left to right, but you can easily customize movement along different axes and directions. You can also choose to use the macro mid-print, depending on your printer's configuration and brush location.

Brush Patterns: The macro currently supports one pattern: a diagonal sweep. This pattern can be extended to other patterns in the future.

Adjustable Brush Parameters: You can set variables for brush location (X, Y, Z), brush size in mm (X, Y, Z), step size, z-step which lowers the height by the amount specified after each iteration, offset, repeat count, speed, diagonal angle, and more. These variables enable precise control over brushing behavior.

Retraction and Temperature Control: You can configure retraction before, during, and after brushing. Temperature-based settings allow the macro to automatically heat the nozzle before brushing if required, as well as home automatically if needed. 

Verbose Output: Enable verbose console output to see detailed information about the brushing process, including axis values, calculations, positioning points and more. 

What makes this macro truly unique is this macro is adaptable to work with all printers with different brush sizes and locations, and rather than forcing moves over the brush in the specific location of your printer, a list of all coordinates in the entire brushing sequence will be generated first, meaning points can be adjusted ahead of time to ensure they stay within limits, almost entirely removing the possibility the macro will error out. If any generated points are found to be outside the printer's limits they will be adjusted to be within. Once the list has been generated the macro simply runs the nozzle through the list of coordinates until complete. 

<h2>How to Use KOMB</h2>

Ensure you have Klipper firmware installed on your 3D printer.

Copy the provided KOMB macro code into your Klipper configuration file where you keep your macros (usually printer.cfg).

Modify the variables defined in the _KOMB_Variables section to match your brushing requirements.

Save the configuration file and reload the Klipper configuration to apply the changes.

Use your printer's UI to carefully find the exact XY position of your brush, use the bottom left corner, you can specific to 0.1mm. 

Then use either calipers to measure the size or use the UI again find to the size by moving to the opposite corner on the upper right and then subtract the the lower left position from the upper right on x and y. 

Note: There's no need to set the size to larger than the brush if you want the strokes to go outside the brush, there's an offset option for this purpose, make sure to set the exact size of the brush to ensure the macro will work correctly.

Then do the same thing with the Z position. take note of the height you want brushing to occur at. Note there is an option to lower the nozzle with each iteration so keep this in mind when deciding your z position. Again, you can be specific to 0.1mm, and same for the z_step size.

Lower your nozzle into your brush until it gets to the maximum depth you want it to be able to get to, then subtract that from the Z position to get the size of the depth and then enter these values into the variables file. The step size defines the spacing between strokes and can be specific to 0.1mm.

Use KOMB by executing it in the console, with a UI macro button, or simply add "KOMB" to your start print macro, preferably before your line purge, to brush before starting every print

The macro will execute the brushing sequence based on the provided parameters. You can monitor the progress through the console output by enabling verbose output. Make sure all variables are set properly to ensure you get the intended behavior. 

Enjoy the enhanced brushing capabilities provided by KOMB!

<h3>Important Notes</h3>

This macro is designed to work with a range of variables and parameters. Make sure to adjust them according to your printer's specifications and your brushing needs.

Since this macro involves moving the printer's nozzle, exercise caution to avoid any collisions during the brushing process and ensure all values are correct. It is recommended to test the macro at low speed.

KOMB is a work in progress, and not all variable combinations have been thoroughly tested. Your feedback and contributions to improve the macro are highly appreciated.

If you encounter any issues, have suggestions for improvements, or wish to contribute to the development of KOMB, please feel free to open an issue or submit a pull request on the GitHub repository.
