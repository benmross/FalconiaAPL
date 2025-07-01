# ParaView XR + ALVR Workaround Options

## Current Issue
ParaView XR segfaults when connecting to ALVR/SteamVR on Arch Linux.

## Workaround Solutions for Presentation

### Option 1: Desktop Demo First
1. Run `./start_presentation_demo.sh`
2. Show tracking working in desktop ParaView
3. Explain that VR would work with native headset connection
4. Demonstrate the concept without actual VR

### Option 2: Try Different OpenXR Runtime
```bash
# Switch from SteamVR to Monado (if available)
sudo pacman -S monado
export XR_RUNTIME_JSON=/usr/share/openxr/1/openxr_monado.json
./start_vr_demo.sh
```

### Option 3: Use Native Quest Link
- Use official Quest Link instead of ALVR
- Or use Virtual Desktop in VR mode
- May have better OpenXR compatibility

### Option 4: Presentation Simulation
- Show desktop ParaView with moving rover
- Explain VR integration concept
- Use smartphone VR viewer with desktop screen sharing

## For Johns Hopkins Presentation

### Recommended Approach:
1. **Primary Demo**: Desktop ParaView with live rover tracking
2. **Backup Explanation**: VR integration concept with screenshots
3. **Live Data**: Use actual rover if available, or mock circular movement

### Script to Use:
```bash
./start_presentation_demo.sh
```

This gives you a working demonstration of the core concept without VR crashes.