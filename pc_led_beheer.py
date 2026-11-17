"""
PC LED Beheer
=============
Bestuur alle RGB-verlichting van je pc (moederbord, CPU-koeler, videokaart,
RAM, ledstrips, enz.) vanuit één venster, via OpenRGB.

Voorbereiding:
  1. Installeer OpenRGB: https://openrgb.org  (Windows/Linux)
  2. Start OpenRGB -> tabblad "SDK Server" -> klik "Start Server"
     (of start OpenRGB met:  OpenRGB.exe --server)
  3. Sluit andere RGB-software (iCUE, Armoury Crate, MSI Center, ...) want die
     kan de aansturing blokkeren.
  4. pip install openrgb-python
  5. python pc_led_beheer.py
"""

import colorsys
import json
import math
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor


def scaled(rgb, factor):
    """Kleur (r,g,b) schalen met helderheid 0..1."""
    return RGBColor(*(max(0, min(255, int(c * factor))) for c in rgb))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC LED Beheer")
        self.geometry("560x640")
        self.minsize(520, 600)

        self.client = None
        self.devices = []
        self.color = (255, 0, 0)
        self.effect_stop = threading.Event()
        self.effect_thread = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.connect()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Server:").pack(side="left")
        self.host = tk.StringVar(value="127.0.0.1")
        ttk.Entry(top, textvariable=self.host, width=14).pack(side="left", padx=4)
        self.port = tk.StringVar(value="6742")
        ttk.Entry(top, textvariable=self.port, width=6).pack(side="left")
        ttk.Button(top, text="Verbinden / Vernieuwen", command=self.connect).pack(side="left", padx=8)
        self.status = ttk.Label(top, text="Niet verbonden", foreground="#b00")
        self.status.pack(side="left")

        dev_box = ttk.LabelFrame(self, text="Apparaten (Ctrl/Shift = meerdere)")
        dev_box.pack(fill="both", expand=True, **pad)
        self.listbox = tk.Listbox(dev_box, selectmode=tk.EXTENDED, exportselection=False, height=9)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.refresh_modes())
        sb = ttk.Scrollbar(dev_box, command=self.listbox.yview)
        sb.pack(side="right", fill="y", pady=6)
        self.listbox.config(yscrollcommand=sb.set)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10)
        ttk.Button(btns, text="Alles selecteren", command=self.select_all).pack(side="left")
        ttk.Button(btns, text="Niets selecteren", command=lambda: self.listbox.selection_clear(0, "end")).pack(side="left", padx=6)

        col = ttk.LabelFrame(self, text="Kleur & helderheid")
        col.pack(fill="x", **pad)
        row = ttk.Frame(col)
        row.pack(fill="x", padx=6, pady=6)
        self.swatch = tk.Label(row, width=6, bg=self._hex(), relief="sunken")
        self.swatch.pack(side="left")
        ttk.Button(row, text="Kies kleur…", command=self.pick_color).pack(side="left", padx=8)
        ttk.Button(row, text="Kleur toepassen", command=self.apply_color).pack(side="left")
        ttk.Button(row, text="Uit", command=self.turn_off).pack(side="left", padx=8)

        br = ttk.Frame(col)
        br.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Label(br, text="Helderheid:").pack(side="left")
        self.brightness = tk.DoubleVar(value=100)
        ttk.Scale(br, from_=0, to=100, variable=self.brightness, command=lambda v: self.live_brightness()).pack(
            side="left", fill="x", expand=True, padx=8)

        mode = ttk.LabelFrame(self, text="Hardware-modus van het apparaat")
        mode.pack(fill="x", **pad)
        mrow = ttk.Frame(mode)
        mrow.pack(fill="x", padx=6, pady=6)
        self.mode_var = tk.StringVar()
        self.mode_box = ttk.Combobox(mrow, textvariable=self.mode_var, state="readonly", width=28)
        self.mode_box.pack(side="left")
        ttk.Button(mrow, text="Modus toepassen", command=self.apply_mode).pack(side="left", padx=8)

        fx = ttk.LabelFrame(self, text="Software-effecten")
        fx.pack(fill="x", **pad)
        frow = ttk.Frame(fx)
        frow.pack(fill="x", padx=6, pady=6)
        ttk.Button(frow, text="Regenboog", command=lambda: self.start_effect("rainbow")).pack(side="left")
        ttk.Button(frow, text="Ademen", command=lambda: self.start_effect("breathe")).pack(side="left", padx=6)
        ttk.Button(frow, text="Kleurwissel", command=lambda: self.start_effect("cycle")).pack(side="left")
        ttk.Button(frow, text="Stop effect", command=self.stop_effect).pack(side="left", padx=6)

        prof = ttk.Frame(self)
        prof.pack(fill="x", **pad)
        ttk.Button(prof, text="Profiel opslaan…", command=self.save_profile).pack(side="left")
        ttk.Button(prof, text="Profiel laden…", command=self.load_profile).pack(side="left", padx=6)

    # ------------------------------------------------------------ helpers
    def _hex(self):
        return "#%02x%02x%02x" % self.color

    def selected(self):
        idx = self.listbox.curselection()
        return [self.devices[i] for i in idx]

    def select_all(self):
        self.listbox.selection_set(0, "end")
        self.refresh_modes()

    def err(self, msg):
        messagebox.showerror("Fout", msg)

    def factor(self):
        return self.brightness.get() / 100.0

    # --------------------------------------------------------- verbinding
    def connect(self):
        self.stop_effect()
        try:
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
            self.client = OpenRGBClient(address=self.host.get(), port=int(self.port.get()), name="PC LED Beheer")
            self.devices = list(self.client.devices)
        except Exception as e:
            self.client, self.devices = None, []
            self.status.config(text="Niet verbonden", foreground="#b00")
            self.listbox.delete(0, "end")
            self.err("Kan niet verbinden met OpenRGB.\n\nStaat de SDK Server aan in OpenRGB?\n\n" + str(e))
            return
        self.status.config(text=f"Verbonden ({len(self.devices)} apparaten)", foreground="#070")
        self.listbox.delete(0, "end")
        for d in self.devices:
            self.listbox.insert("end", f"{d.name}  [{d.type.name.title()}, {len(d.leds)} leds]")
        self.select_all()

    def refresh_modes(self):
        devs = self.selected()
        if not devs:
            self.mode_box["values"] = []
            return
        names = None
        for d in devs:
            n = [m.name for m in d.modes]
            names = n if names is None else [x for x in names if x in n]
        self.mode_box["values"] = names or []
        if names:
            self.mode_var.set(names[0])
        else:
            self.mode_var.set("")

    # -------------------------------------------------------------- acties
    def pick_color(self):
        c = colorchooser.askcolor(color=self._hex(), title="Kies een kleur")
        if c and c[0]:
            self.color = tuple(int(v) for v in c[0])
            self.swatch.config(bg=self._hex())
            self.apply_color()

    @staticmethod
    def ensure_direct(dev):
        names = {m.name.lower(): m.name for m in dev.modes}
        try:
            if dev.active_mode.name.lower() in ("direct", "static"):
                return
        except Exception:
            pass
        for key in ("direct", "static"):
            if key in names:
                dev.set_mode(names[key])
                return

    def apply_color(self):
        self.stop_effect()
        c = scaled(self.color, self.factor())
        for d in self.selected():
            try:
                self.ensure_direct(d)
                d.set_color(c)
            except Exception as e:
                print(f"{d.name}: {e}")

    def live_brightness(self):
        # Alleen direct bijwerken als er geen effect draait
        if not (self.effect_thread and self.effect_thread.is_alive()):
            self.apply_color()

    def turn_off(self):
        self.stop_effect()
        for d in self.selected():
            try:
                self.ensure_direct(d)
                d.set_color(RGBColor(0, 0, 0))
            except Exception as e:
                print(f"{d.name}: {e}")

    def apply_mode(self):
        self.stop_effect()
        name = self.mode_var.get()
        if not name:
            return
        for d in self.selected():
            try:
                if name in [m.name for m in d.modes]:
                    d.set_mode(name)
            except Exception as e:
                print(f"{d.name}: {e}")

    # ------------------------------------------------------------ effecten
    def start_effect(self, kind):
        self.stop_effect()
        devs = self.selected()
        if not devs:
            return
        for d in devs:
            try:
                self.ensure_direct(d)
            except Exception:
                pass
        self.effect_stop = threading.Event()
        self.effect_thread = threading.Thread(target=self._run_effect, args=(kind, devs, self.effect_stop), daemon=True)
        self.effect_thread.start()

    def stop_effect(self):
        self.effect_stop.set()
        t = self.effect_thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1)

    def _run_effect(self, kind, devs, stop):
        t0 = time.time()
        while not stop.is_set():
            t = time.time() - t0
            f = self.factor()
            for d in devs:
                try:
                    n = max(1, len(d.leds))
                    if kind == "rainbow":
                        cols = []
                        for i in range(n):
                            r, g, b = colorsys.hsv_to_rgb((t * 0.15 + i / n) % 1.0, 1, 1)
                            cols.append(scaled((r * 255, g * 255, b * 255), f))
                        d.set_colors(cols)
                    elif kind == "cycle":
                        r, g, b = colorsys.hsv_to_rgb((t * 0.08) % 1.0, 1, 1)
                        d.set_color(scaled((r * 255, g * 255, b * 255), f))
                    elif kind == "breathe":
                        k = (math.sin(t * 2) + 1) / 2
                        d.set_color(scaled(self.color, f * (0.05 + 0.95 * k)))
                except Exception as e:
                    print(f"{d.name}: {e}")
            stop.wait(0.05)

    # ------------------------------------------------------------- profielen
    def save_profile(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Profiel", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"color": self.color, "brightness": self.brightness.get(), "mode": self.mode_var.get()}, fh)

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[("Profiel", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                p = json.load(fh)
            self.color = tuple(p["color"])
            self.brightness.set(p.get("brightness", 100))
            self.swatch.config(bg=self._hex())
            self.apply_color()
        except Exception as e:
            self.err(f"Profiel kon niet geladen worden: {e}")

    def on_close(self):
        self.stop_effect()
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
