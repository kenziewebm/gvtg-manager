#!/usr/bin/env python3
import re
import os
import uuid
import subprocess
import tkinter as tk
from tkinter import messagebox

font = ("Monospace", 10)

class VGPUCreationWizard(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("vGPU Setup Wizard")
        self.resizable(False,False)
        self.attributes("-type","dialog")
        self.geometry('450x300')

        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.vgpu_name_label = tk.Label(self.top_frame, text="vGPU Name:", font=font)
        self.vgpu_name_label.pack(side=tk.LEFT, pady=5, padx=5)

        self.name_entry = tk.Entry(self.top_frame, width=45, font=font)
        self.name_entry.insert(0, str(uuid.uuid4()))
        self.name_entry.pack(side=tk.RIGHT, pady=5, padx=5)
        
        self.middle_frame = tk.Frame(self)
        self.middle_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.vgpu_mode_list_label = tk.Label(self.middle_frame, font=font, text="Select vGPU mode:")
        self.vgpu_mode_list_label.pack(side=tk.TOP, fill=tk.X)

        self.vgpu_mode_list = tk.Listbox(self.middle_frame, width=45, height=5, font=font, borderwidth=2)
        self.vgpu_mode_list.pack(fill=tk.X, expand=True, pady=5, ipady=2)

        self.populate_vgpu_mode_list()
        self.vgpu_mode_list.select_set(0) # default selection

        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.create_button = tk.Button(self.bottom_frame, text="Create vGPU", command=self.create_vgpu, font=font, width=25)
        self.create_button.pack(side=tk.LEFT, pady=10, expand=True)

        self.cancel_button = tk.Button(self.bottom_frame, text="Cancel", command=self.destroy, font=font, width=25)
        self.cancel_button.pack(side=tk.RIGHT, pady=10, expand=True)
        
        # Center the window on parent
        self.geometry("+{}+{}".format(parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
    def create_vgpu(self):
        vgpu_name = self.name_entry.get()
        if vgpu_name == "pumpkin":
            messagebox.showinfo("Info", "For personal use, of course ;)")
        pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$')
        if bool(pattern.match(vgpu_name)) is False:
            messagebox.showerror("Error", "vGPU name does not match uuid4 format\n(Hint: use the `uuidgen` command]")
            return

        vgpu_mode = self.vgpu_mode_list.curselection()[0]
        vgpu_mode = self.vgpu_mode_list.get(vgpu_mode).split(" ")[0]

        pcie_addr = self.get_igpu_pcie_addr()
        try:
            f = open(f"/sys/devices/pci0000:00/{pcie_addr}/mdev_supported_types/{vgpu_mode}/create", 'w')
            f.write(vgpu_name)
            f.close()
        except Exception as e:
            messagebox.showerror("Error", f"{e}\n(Hint: you probably need to run this app as root)")

        self.parent.populate_vgpu_list()
        self.destroy()


    def get_igpu_pcie_addr(self):
        try:
            lspci = subprocess.check_output(['lspci', '-D', '-nn'], text=True)
            display = [line for line in lspci.split('\n') if 'Display' in line or 'VGA' in line]
            pcie_addr = [line.split()[0] for line in display][0]
            return pcie_addr
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get iGPU address!\nPlease report this as a bug!\n{e}")


    def populate_vgpu_mode_list(self):
        try:
            pcie_addr = self.get_igpu_pcie_addr()
            basedir = f"/sys/devices/pci0000:00/{pcie_addr}/mdev_supported_types"

            modes = os.listdir(basedir)
            for mode in modes:
                path = os.path.join(basedir, mode)
                with open(os.path.join(path, 'description'), 'r') as f:
                    desc = f.read()
                for line in desc.split('\n'):
                    if "resolution" in line:
                        res = line.strip()
                    if "high_gm_size" in line:
                        vram = line.replace("high_gm_size", "vram").strip()
                self.vgpu_mode_list.insert(tk.END, f"{mode} | {res} / {vram}")
        except Exception as e:
            self.vgpu_mode_list.insert(tk.END, "Unknown error:")
            self.vgpu_mode_list.insert(tk.END, e)

class VGPUManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("vGPU Manager")
        self.resizable(False,False)
        self.attributes("-type", "dialog")
        self.geometry('850x350')
        
        self.vgpu_list_frame = tk.Frame(self)
        self.vgpu_list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10, ipady=2)
        
        self.vgpu_list_label = tk.Label(self.vgpu_list_frame, text="vGPUs:", font=font)
        self.vgpu_list_label.pack(anchor=tk.W, expand=True, pady=5, ipady=2)
        
        self.vgpu_listbox = tk.Listbox(self.vgpu_list_frame, width=45, height=10, font=font, borderwidth=2)
        self.vgpu_listbox.pack(fill=tk.X, expand=True, pady=5, ipady=2)
        
        self.vgpu_listbox.bind("<<ListboxSelect>>", self.on_vgpu_select)

        self.populate_vgpu_list()

        self.add_vgpu_button = tk.Button(self.vgpu_list_frame, text="New vGPU", command=self.create_vgpu, width=40, font=font)
        self.add_vgpu_button.pack(side=tk.LEFT, expand=True, pady=5, padx=5, ipady=2)
        
        self.details_frame = tk.Frame(self)
        self.details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10, ipady=2)
        
        self.details_label = tk.Label(self.details_frame, text="Details:", font=font)
        self.details_label.pack(anchor=tk.W, expand=True, pady=5, ipady=2)

        self.details_text = tk.Text(self.details_frame, height=10, width=45, font=font, borderwidth=2)
        self.details_text.pack(fill=tk.X, expand=True, pady=5, ipady=6) # hours wasted on getting this shit to align properly: 3

        self.delete_button = tk.Button(self.details_frame, text="Delete", command=self.delete_vgpu, width=25, font=font)
        self.delete_button.pack(side=tk.LEFT, expand=True, padx=5, pady=5, ipady=2)
        
        self.copy_qemu_button = tk.Button(self.details_frame, text="Copy QEMU flag", command=self.copy_qemu_cmd, width=25, font=font)
        self.copy_qemu_button.pack(side=tk.RIGHT, expand=True, padx=5, pady=5, ipady=2)

        self.update()
        
        try:
            self.populate_details(list_vgpus()[0])
        except Exception:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, "No vGPUs detected.")
        
    def on_vgpu_select(self, event):
        selection = event.widget.curselection()
        if selection:
            vgpu = event.widget.get(selection[0])
            self.populate_details(vgpu)

    def populate_vgpu_list(self):
        self.vgpu_listbox.delete(0, tk.END)
        vgpus = self.list_vgpus()
        for vgpu in vgpus:
            self.vgpu_listbox.insert(tk.END, vgpu)

    def list_vgpus(self):
        path = '/sys/bus/mdev/devices/'
        try:
            dirs = os.listdir(path)
            vgpus = [folder for folder in dirs]
            return vgpus
        except FileNotFoundError:
            return []

    def populate_details(self, name):
        self.details_text.delete(1.0, tk.END)
        
        file = f"/sys/bus/mdev/devices/{name}/mdev_type/description"

        try:
            f = open(file, 'r')
            details = {}
            for line in f:
                key, value = line.strip().split(': ')
                details[key.strip()] = value.strip()

            details_txt =  f"UUID: {name}\n"
            details_txt += f"VRAM size: {details.get('high_gm_size', 'N/A')}\n"
            details_txt += f"Max resolution: {details.get('resolution', 'N/A')}\n"
            details_txt += f"Device path: /sys/bus/mdev/devices/{name}\n"
        
            self.details_text.insert(tk.END, details_txt)

        except Exception as e:
            self.details_txt = f"Error: {e}\n"
        
    def delete_vgpu(self):
        selected = self.vgpu_listbox.curselection()
        if selected:
            vgpu_name = self.vgpu_listbox.get(selected[0])
            try:
                f = open(f"/sys/bus/mdev/devices/{vgpu_name}/remove", "w")
                f.write("1")
                f.close()
                self.update()
                self.populate_vgpu_list()
                self.details_text.delete(1.0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"{e}\n(Hint: try running this app as root)")
        else:
            messagebox.showerror("Error", "Try selecting a vGPU first.")
    
    def copy_qemu_cmd(self):
        sel = self.vgpu_listbox.curselection()
        if sel:
            vgpu_name = self.vgpu_listbox.get(sel[0])
            self.clipboard_clear()
            self.clipboard_append(f"-device vfio-pci,sysfsdev=/sys/bus/mdev/devices/{vgpu_name},display=on,x-igd-opregion=on,ramfb=on,driver=vfio-pci-nohotplug")
            # make clipboard persist when window is closed
            # firefox should take notes 
            self.update()
            messagebox.showinfo("Info", "Copied QEMU flag.")
        else:
            messagebox.showerror("Error", "Try selecting a vGPU first")

    def create_vgpu(self):
        create_wizard = VGPUCreationWizard(self)
        self.wait_window(create_wizard)


if __name__ == "__main__":
    app = VGPUManager()
    app.mainloop()

