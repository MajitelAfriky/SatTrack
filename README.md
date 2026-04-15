# SatTrack *(work in progress)*

SatTrack is a comprehensive satellite tracking system that combines custom software control with precision hardware. The project integrates a specialized software stack with hardware designs to provide a complete solution for automated satellite observation.

## System Overview

- **Core Hardware:** The system is powered by the **Raspberry Pi Pico 2 W**, providing efficient processing for motor control, with possible use of wireless communication.
- **Mechanical Design:** The physical rotator structure is based on the [CounterRotator](https://github.com/NicolasGagne/CounterRotator) models developed by Nicolas Gagne.
- **Software Integration:** SatTrack communicates with **Gpredict** using the **Hamlib** protocol (`rotctld`). This allows for seamless, real-time antenna positioning based on orbital data.

## Features

- Real-time tracking of satellite positions.
- Modular architecture for easy updates and hardware integration.

## Project Structure

- `data/` - Contains data files, configurations and calibrations required for tracking.
- `lib/` - Custom or external libraries and dependencies.
- `src/` - Core source code for the tracking and control logic.
- `main.py` - The main entry point of the application.

## Acknowledgments
Special thanks to Nicolas Gagne. The 3D models and mechanical concepts used for the hardware aspect of this project were sourced from the CounterRotator project:
https://github.com/NicolasGagne/CounterRotator
