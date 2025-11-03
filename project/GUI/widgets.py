# import tkinter as tk
# from tkinter import ttk

# # Theme toggle (dark / light)
# def apply_theme(root, dark_mode: bool = False, widgets: tuple | list = ()):
#     """
#     root: okno główne
#     dark: True = dark mode, False = light mode
#     widgets: opcjonalna lista widgetów (np. left, right, text) które trzeba dodatkowo skonfigurować
#     """
#     style = ttk.Style(root)

#     try:
#         style.theme_use("clam")
#     except tk.TclError as e:
#         # obsłuż brak motywu
#         style.theme_use("default")
#         print(f"Błąd ustawienia motywu: {e}")

#     if dark_mode:
#         colors = {
#             "bg": "#2e2e2e",
#             "fg": "#eaeaea",
#             "button_bg": "#444444",
#             "button_hover_bg": "#555555",
#             "button_active_bg": "#666666",
#             "button_active_fg": "#ffffff",
#             "text_bg": "#1e1e1e",
#             "text_fg": "#dcdcdc",
#         }
#     else:
#         colors = {
#             "bg": "#f0f0f0",
#             "fg": "#000000",
#             "button_bg": "#e0e0e0",
#             "button_hover_bg": "#d0d0d0",
#             "button_active_bg": "#c0c0c0",
#             "button_active_fg": "#000000",
#             "text_bg": "#ffffff",
#             "text_fg": "#000000",
#         }
    
#     # root and ttk styles
#     root.configure(bg=colors["bg"])
#     style.configure("TFrame", background=colors["bg"])
#     style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
#     style.configure("TButton", background=colors["button_bg"], foreground=colors["fg"])
#     # styl dla checkbutton i styl hover (używany przy bind)
#     style.configure("TCheckbutton", background=colors["bg"], foreground=colors["fg"])
#     style.configure("Hover.TCheckbutton", background=colors["button_hover_bg"], foreground=colors["button_active_fg"])

#     # map dla ttk.Button (opcjonalne)
#     style.map(
#         "TButton",
#         background=[("active", colors["button_hover_bg"]), ("pressed", colors["button_active_bg"]), ("!disabled", colors["button_bg"])],
#         foreground=[("active", colors["button_active_fg"]), ("pressed", colors["button_active_fg"]), ("!disabled", colors["fg"])],
#     )


#     style.map(
#         "TButton",
#         background=[("active", colors["button_hover_bg"]), ("!disabled", colors["bg"])],
#         foreground=[("active", colors["button_active_fg"]), ("!disabled", colors["fg"])],
#     )

#     for widget in widgets:
#         try:
#             if isinstance(widget, tk.Text):
#                 widget.configure(bg=colors["text_bg"], fg=colors["text_fg"], insertbackground=colors["fg"])
#             elif isinstance(widget, tk.Checkbutton) or isinstance(widget, tk.Button):
#                 # tk widgets: ustaw tło, aktywne kolory i kolor tekstu
#                 widget.configure(
#                     bg=colors["button_bg"],
#                     fg=colors["fg"],
#                     activebackground=colors["button_hover_bg"],
#                     activeforeground=colors["button_active_fg"],
#                     selectcolor=colors["bg"],    # kolor obszaru przy zaznaczeniu (checkbox)
#                     highlightbackground=colors["bg"],
#                     highlightcolor=colors["bg"],
#                 )
#                 # zapamiętujemy kolory na widgetcie do użycia w bindach
#                 setattr(widget, "_theme_colors", colors)
#             else:
#                 widget.configure(bg=colors["bg"])
#         except Exception:
#             pass