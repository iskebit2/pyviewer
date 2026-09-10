import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import copy


class dataPanel(ttk.LabelFrame):

    def __init__(self, parent, data, title="Parametreler", **kwargs):
        super().__init__(parent, text=title, padding=12, **kwargs)

        self.data = data
        self.original = copy.deepcopy(data)
        self.vars = {}
        self.entries = {}

        self._build()

    # ---------------------------------------------------------

    def _build(self):

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            body,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=canvas.yview
        )

        frame = ttk.Frame(canvas)

        frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window(
            (0, 0),
            window=frame,
            anchor="nw"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        frame.columnconfigure(1, weight=1)

        for row, (key, value) in enumerate(self.data.items()):

            label = ttk.Label(
                frame,
                text=key
            )

            label.grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 15),
                pady=5
            )

            var = tk.StringVar(
                value=str(value)
            )

            self.vars[key] = var

            if isinstance(value, bool):

                widget = ttk.Checkbutton(
                    frame,
                    variable=var,
                    onvalue="True",
                    offvalue="False"
                )

            else:

                widget = ttk.Entry(
                    frame,
                    textvariable=var,
                    width=25
                )

            widget.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=3
            )

            self.entries[key] = widget

        # -------------------------------------------------
        # Butonlar
        # -------------------------------------------------

        buttons = ttk.Frame(self)
        buttons.pack(
            fill="x",
            pady=(12, 0)
        )

        ttk.Button(
            buttons,
            text="Geri Al",
            command=self.reset
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="İptal",
            command=self.cancel
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="✓ Kaydet",
            command=self.save
        ).pack(
            side="right",
            padx=(0, 6)
        )

    # ---------------------------------------------------------

    def _convert(self, value, original):

        if isinstance(original, bool):
            return value == "True"

        if isinstance(original, int):
            return int(value)

        if isinstance(original, float):
            return float(value)

        if original is None:
            return value

        return value

    # ---------------------------------------------------------

    def save(self):

        try:

            for key, original in self.original.items():

                value = self.vars[key].get()

                self.data[key] = self._convert(
                    value,
                    original
                )

            self.original = copy.deepcopy(self.data)

        except (ValueError, TypeError) as e:

            tk.messagebox.showerror(
                "Geçersiz Değer",
                f"'{key}' için geçersiz değer:\n\n{e}",
                parent=self.winfo_toplevel()
            )

    # ---------------------------------------------------------

    def reset(self):

        for key, value in self.original.items():

            self.vars[key].set(str(value))

    # ---------------------------------------------------------

    def cancel(self):

        self.data.clear()
        self.data.update(
            copy.deepcopy(self.original)
        )

        self.winfo_toplevel().destroy()

    # ---------------------------------------------------------

    def get(self):

        return self.data
        
if __name__ == "__main__":
    
    myconfig = {
        'b': 8.21,
        'd': 4.56,
        'z0': 0.0,
        'z1': 10.45,
        'z2': 11.344,
        'v_b0': 28.0,
        'egim': 21.43,
        'roof_type': 'Beşik',
        'mahya_paralel': 'b',
        'terrain': 'Kategori III'
    }

    root = tk.Tk()

    panel = dataPanel(
        root,
        myconfig,
        title="Rüzgar Parametreleri"
    )

    panel.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15
    )

    root.mainloop()