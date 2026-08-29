# Eagle-1-64Bit

An action-packed game inspired by Helldivers, where you pilot an Eagle-1 gunship providing air support to ground forces while engaging aerial threats like Stingrays.

## Overview

Eagle-1-64Bit is a Python-based game that combines aerial combat and ground support mechanics. Take to the skies as a skilled pilot, defend your squad on the ground, and dogfight enemy aircraft in [...]

## Gameplay Features

- **Aerial Combat**: Engage in fast-paced dogfighting with enemy aircraft
- **Ground Support**: Provide tactical air support to allied ground forces
- **Enemy Variety**: Face different aerial threats including Stingrays and other airborne enemies
- **Gunship Mechanics**: Control and manage your Eagle-1 gunship with authentic flight mechanics

## Technical Details

- **Language**: Python
- **Architecture**: 64-bit optimized

## Project Status

This is an active development project. Features and gameplay mechanics are currently being implemented.

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/paulp143/Eagle-1-64Bit.git
   cd Eagle-1-64Bit
   ```

2. Install dependencies (add your requirements here):
   ```bash
   pip install -r requirements.txt
   ```

### Running the Game

```bash
python main.py
```

## Controls

Below are the default controls for playing Eagle-1-64Bit. These cover keyboard and common gamepad mappings. If your project implements remappable controls or an in-game options menu, update this section accordingly.

Keyboard (default)

- Movement / Flight
  - W: Thrust forward / increase throttle
  - S: Thrust backward / decrease throttle / reverse
  - A: Roll / strafe left
  - D: Roll / strafe right
  - Q / E: Yaw left / right (rudder)
  - Space: Boost / afterburner (hold)
  - Left Shift: Toggle hover / precision mode (hold for slow, fine control)

- Weapons & Combat
  - Left Mouse Button: Primary fire (guns / continuous fire)
  - Right Mouse Button: Secondary fire / alt-weapon (missiles, bombs)
  - R: Reload / cycle weapon (if applicable)
  - T: Target nearest enemy
  - G: Deploy countermeasures (flares / chaff)

- Support & Interaction
  - F: Call in support / request ground support
  - C: Camera view change / cycle cameras
  - Tab: Show radar / mission objectives overlay
  - M: Toggle map

- Misc
  - Esc: Pause / open menu
  - Enter: Confirm / interact
  - Backspace: Quick chat / voice command (if implemented)

Gamepad (recommended mapping)

- Left Stick: Pitch / Roll (flight control)
- Right Stick: Look / Aim
- Left Trigger (LT): Throttle down / brake (precision)
- Right Trigger (RT): Primary fire
- Left Bumper (LB): Secondary fire / alternate weapon
- Right Bumper (RB): Cycle weapons / special action
- A (or Bottom Button): Boost
- B (or Right Button): Deploy countermeasures
- X (or Left Button): Call support / interact
- Y (or Top Button): Toggle camera view
- Start: Pause / Menu
- Back: Map / Objectives

Mouse

- Move mouse: Aim / look
- Scroll wheel: Cycle weapons / zoom
- Mouse sensitivity: Adjustable in options (if implemented)

Customizing Controls

- These are the default controls. If your game implements in-game control remapping, controller configuration files, or a JSON/YAML config, update this README to explain where to change bindings (e.g., `config/controls.json` or an in-game Options -> Controls menu).

Tips & Best Practices

- Use Boost (Space / A) to quickly disengage or close distance, but watch your throttle to avoid overshooting friendly targets.
- Toggle hover/precision mode for tight strafing runs during ground support missions.
- Use countermeasures (G / B) when missiles lock on to you — timing matters.
- Cycle targets while keeping an eye on the radar (Tab) to prioritize high-threat enemies like Stingrays.

## Project Structure

```
Eagle-1-64Bit/
├── README.md
└── [Game code files]
```

## Contributing

Contributions are welcome! Feel free to fork this repository and submit pull requests.

## License

[Add your license information here]

## Inspiration

Inspired by Helldivers and classic gunship arcade games.

---

**Note**: This project is in active development. Check back for updates and new features!
