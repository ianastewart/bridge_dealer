import tkinter as tk

root = tk.Tk()
root.title("Hello from PyCharm Remote Debug")
root.geometry("300x200")

label = tk.Label(root, text="This is running on the Pi's screen")
label.pack(expand=True)

root.mainloop()