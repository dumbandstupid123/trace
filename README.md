
# Trace

Trace is a tool I built to get fast electronic diagrams and BOM's while prototyping.
It does two things:

---

### 1. Natural Language → Schematic + BOM

Describe what you want to build in plain English and Trace will design a rough circuit for you — picks real components, looks up current Digikey prices, and gives you a full BOM with clickable links. You can export the whole thing as a PDF.

I tested it with prompts ranging from "ESP32 with USB charging" to "full autonomous drone flight controller with dual-core MCU, CAN FD, GPS, ESC outputs, and 48V power chain." It handles both.

<img width="979" height="409" alt="Screenshot 2026-02-25 at 3 24 44 AM" src="https://github.com/user-attachments/assets/1e67bc97-4598-427b-b28a-0f07402a9b87" />


### 1. Datasheet → Zener Code

Drop in any component datasheet (PDF) and trace will read it, understand the pinout, power requirements, and recommended circuitry, and spit out verified Zener code — Diode's hardware description language. It runs the code through the `pcb build` compiler automatically and retries if it fails.

I tested it on ESP32, STM32, and IMU datasheets. It gets it right most of the time on the first try.

### How to run it

You'll need the Diode `pcb` CLI installed for the Zener feature.

```bash
# install dependencies
pip3 install anthropic flask flask-cors python-dotenv pdfplumber

# add your Anthropic API key
echo 'ANTHROPIC_API_KEY=your-key-here' > .env

# start the server
python3 app.py

# open the frontend
open index.html
```

---

### What I learned
The hardest part was getting the compiler feedback loop right — the agent needs to actually understand the error messages and fix them, not just retry blindly.
The footprint resolution step (for PCB layout) requires Diode's internal infrastructure, which I don't have access to. That's the one piece I couldn't close without them.

---

built by sandeep ramlochan — sr185@rice.edu
