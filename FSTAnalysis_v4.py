import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import tempfile
import os
import re
from datetime import datetime

population_history = []
history_index = -1

def clear_output():
    answer = messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the output?")
    if answer:
        output_text.delete('1.0', tk.END)

custom_r_code = None  # Persistent variable to store modified R code

def format_pops(input_str):
    clean_input = input_str.replace('"', '').replace("'", '')
    pops = [p.strip() for p in re.split(r'[,\s]+', clean_input) if p.strip()]
    return ','.join(f'"{p}"' for p in pops)


def get_r_library_paths(rscript_path='Rscript'):
    try:
        result = subprocess.run(
            [rscript_path, '-e', 'cat(.libPaths())'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        paths_raw = result.stdout.strip()
        paths = re.findall(r'\/[^\s"]+', paths_raw)
        return paths
    except Exception:
        return []

def check_package_in_paths(package_name, paths):
    for path in paths:
        if os.path.isdir(os.path.join(path, package_name)):
            return path
    return None

def run_fst_analysis():
    pop1_raw = pop1_entry.get()
    pop2_raw = pop2_entry.get()
    dataset_prefix = prefix_entry.get().strip()
    f2_dir = f2_entry.get().strip()
    adjust_ph = pseudohaploid_var.get()
    r_folder = r_folder_entry.get().strip()

    if not (pop1_raw and pop2_raw and dataset_prefix and f2_dir and r_folder):
        messagebox.showerror("Missing info", "Please fill in all fields.")
        return

    rscript_path = os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')
    if not os.path.isfile(rscript_path):
        messagebox.showerror("Rscript not found", f"Rscript.exe not found at expected location:\n{rscript_path}")
        return

    # Fix: Remove these R-style lines from Python code
    # pop1 <- c({pop1})
    # pop2 <- c({pop2})
    # mypops = c(pop1, pop2)  # This is correct R syntax

    # Instead, format the population strings properly
    pop1 = format_pops(pop1_raw)
    pop2 = format_pops(pop2_raw)
    
    r_lib_paths = get_r_library_paths(rscript_path)
    package_path = check_package_in_paths("admixtools", r_lib_paths)
    lib_path_code = f'.libPaths("{package_path}")\n' if package_path else ''

    adj_flag = "TRUE" if adjust_ph else "FALSE"

    r_code = f"""
{lib_path_code}
library(admixtools)
library(tidyverse)

prefix = "{dataset_prefix}"
my_f2_dir = "{f2_dir}"

# Explicit population definitions
pop1 <- c({pop1})
pop2 <- c({pop2})
mypops <- c({pop1}, {pop2})  # Combined directly

extract_f2(prefix, my_f2_dir, pops = c(mypops), overwrite = TRUE, maxmiss = 1)
f2_blocks = f2_from_precomp(my_f2_dir, pops = mypops, afprod = TRUE)

fst_result <- fst(data = prefix, pop1 = pop1, pop2 = pop2, boot = FALSE, adjust_pseudohaploid = {adj_flag})
print(fst_result, n = Inf)
"""


    with tempfile.NamedTemporaryFile(delete=False, suffix=".R") as r_script:
        r_script.write(r_code.encode('utf-8'))
        r_script_path = r_script.name

    try:
        process = subprocess.Popen(
            [rscript_path, r_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        output_text.insert(tk.END, f"\n--- Run started at {datetime.now()} ---\n")
        output_text.insert(tk.END, f"Pop1: {pop1_raw}\nPop2: {pop2_raw}\n\n")
        output_text.see(tk.END)

        # Buffer to store the last SNP read line
        last_snp_line = ""

        for line in process.stdout:
            if "SNPs read" in line:
                # Strip and overwrite the previous SNP line
                last_snp_line = line.strip()
                output_text.delete("end-2l", "end-1l")
                output_text.insert(tk.END, last_snp_line + "\n")
            else:
                output_text.insert(tk.END, line)
            output_text.see(tk.END)

        process.wait()
        status_label.config(text="FST analysis completed.")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        os.remove(r_script_path)

def edit_and_run_r_code():
    global custom_r_code

    dataset_prefix = prefix_entry.get().strip()
    f2_dir = f2_entry.get().strip()
    r_folder = r_folder_entry.get().strip()
    adjust_ph = pseudohaploid_var.get()

    if not r_folder:
        messagebox.showerror("Missing R folder", "Please specify the R installation folder.")
        return

    rscript_path = os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')
    if not os.path.isfile(rscript_path):
        messagebox.showerror("Rscript not found", f"Rscript.exe not found at:\n{rscript_path}")
        return

    r_lib_paths = get_r_library_paths(rscript_path)
    package_path = check_package_in_paths("admixtools", r_lib_paths)
    lib_path_code = f'.libPaths("{package_path}")\n' if package_path else ''
    adj_flag = "TRUE" if adjust_ph else "FALSE"

    default_r_code = f"""
{lib_path_code}
library(admixtools)
library(tidyverse)

prefix = "{dataset_prefix}"
my_f2_dir = "{f2_dir}"

# Edit these manually:
pop1 <- c("POP1")  # Replace with your actual population
pop2 <- c("POP2")  # Replace with your actual population
mypops = c(pop1, pop2)

extract_f2(prefix, my_f2_dir, pops = c(mypops), overwrite = TRUE, maxmiss = 1)
f2_blocks = f2_from_precomp(my_f2_dir, pops = mypops, afprod = TRUE)

fst_result <- fst(data = prefix, pop1 = pop1, pop2 = pop2, boot = FALSE, adjust_pseudohaploid = FALSE)
print(fst_result, n = Inf)
""".strip()

    if custom_r_code is None:
        custom_r_code = default_r_code

    editor_win = tk.Toplevel(root)
    editor_win.attributes('-topmost', True)
    editor_win.title("Edit FST R Code")

    def enforce_always_on_top():
        try:
            editor_win.attributes("-topmost", True)
        except tk.TclError:
            return  # Window likely closed
        editor_win.after(1000, enforce_always_on_top)

    enforce_always_on_top()  # Start the loop

    text_editor = tk.Text(editor_win, wrap=tk.NONE, width=100, height=30, undo=True)
    text_editor.insert('1.0', custom_r_code)
    text_editor.pack(fill=tk.BOTH, expand=True)

    def run_edited_r_code():
        global custom_r_code
        edited_code = text_editor.get("1.0", tk.END)
        custom_r_code = edited_code

        with tempfile.NamedTemporaryFile(delete=False, suffix=".R") as temp_r_file:
            temp_r_file.write(edited_code.encode('utf-8'))
            r_script_path = temp_r_file.name

        try:
            process = subprocess.Popen(
                [rscript_path, r_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            output_text.insert(tk.END, f"\n---\n[Custom FST R Code Output - {timestamp}]\n")

            # Buffer to store the last SNP read line
            last_snp_line = ""

            for line in process.stdout:
                if "SNPs read" in line:
                    # Strip and overwrite the previous SNP line
                    last_snp_line = line.strip()
                    output_text.delete("end-2l", "end-1l")
                    output_text.insert(tk.END, last_snp_line + "\n")
                else:
                    output_text.insert(tk.END, line)
                output_text.see(tk.END)

            process.wait()
            status_label.config(text="Custom R code executed.")
        except Exception as e:
            messagebox.showerror("Execution Error", str(e))
        finally:
            os.remove(r_script_path)

    def save_edited_code():
        global custom_r_code
        custom_r_code = text_editor.get("1.0", tk.END)
        status_label.config(text="Code saved.")

    def restore_original_code():
        nonlocal text_editor
        text_editor.delete("1.0", tk.END)
        text_editor.insert("1.0", default_r_code)
        status_label.config(text="Original code restored.")

    def on_editor_close():
        current_code = text_editor.get("1.0", tk.END)
    # Always save the edited code before closing
        global custom_r_code
        custom_r_code = current_code
        editor_win.destroy()

    editor_win.protocol("WM_DELETE_WINDOW", on_editor_close)

    button_frame = tk.Frame(editor_win)
    button_frame.pack(fill=tk.X, pady=5)

    tk.Button(button_frame, text="Restore Original Code", command=restore_original_code, bg="orange").pack(side=tk.LEFT, padx=5)
    tk.Button(editor_win, text="Run This Code", command=run_edited_r_code, bg="lightgreen").pack(pady=5)


# --- MAIN WINDOW SETUP WITH SCROLLBAR ---
root = tk.Tk()
root.title("FST Runner (admixtools)")

# Create main frame with scrollbar
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=1)

canvas = tk.Canvas(main_frame)
scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# --- GUI ELEMENTS ---
tk.Label(scrollable_frame, text="Pop1 (single or comma-separated):").grid(row=0, column=0, sticky='w')
pop1_entry = tk.Entry(scrollable_frame, width=70)
pop1_entry.grid(row=0, column=1, columnspan=2, pady=2, sticky='we')

tk.Label(scrollable_frame, text="Pop2 (one or more):").grid(row=1, column=0, sticky='w')

# Use StringVar to enable syncing with the popup editor
pop2_var = tk.StringVar()
pop2_entry = tk.Entry(scrollable_frame, width=70, textvariable=pop2_var)
pop2_entry.grid(row=1, column=1, columnspan=2, pady=2, sticky='we')

# Add small button next to pop2 to open large editor
def open_large_pop2_editor():
    top = tk.Toplevel(root)
    top.title("Edit Pop2 - Large View")
    top.geometry("800x400")
    top.resizable(True, True)

    # Keep the window on top permanently
    top.attributes("-topmost", True)

    def keep_on_top():
        top.attributes("-topmost", True)  # Reapply the attribute
        top.after(1000, keep_on_top)  # Repeat every second

    keep_on_top()  # Start the loop

    # Create text editor
    text = tk.Text(top, wrap=tk.WORD, font=("Consolas", 12))
    text.pack(expand=True, fill="both")
    text.insert("1.0", pop2_var.get())

    # Flag to prevent infinite feedback loop
    syncing_from_main = False
    syncing_from_popup = False

    # --- Real-time popup ➝ entry sync ---
    def on_popup_key(event=None):
        nonlocal syncing_from_popup
        syncing_from_popup = True
        pop2_var.set(text.get("1.0", "end-1c"))
        syncing_from_popup = False

    text.bind("<KeyRelease>", on_popup_key)

    # --- Real-time entry ➝ popup sync ---
    def on_var_change(*args):
        nonlocal syncing_from_main
        if not syncing_from_popup:
            syncing_from_main = True
            new_value = pop2_var.get()
            text_content = text.get("1.0", "end-1c")
            if new_value != text_content:
                text.delete("1.0", tk.END)
                text.insert("1.0", new_value)
            syncing_from_main = False

    # Attach the trace
    trace_id = pop2_var.trace_add("write", on_var_change)

    def on_close():
        pop2_var.trace_remove("write", trace_id)
        top.destroy()

    # Add a close button
    tk.Button(top, text="Close", command=on_close).pack(pady=5)

tk.Button(scrollable_frame, text="🡕", width=3, command=open_large_pop2_editor).grid(row=1, column=3, padx=2)

tk.Label(scrollable_frame, text="Dataset prefix (path):").grid(row=2, column=0, sticky='w')
prefix_entry_var = tk.StringVar()
prefix_entry = tk.Entry(scrollable_frame, width=70, textvariable=prefix_entry_var)
prefix_entry.grid(row=2, column=1, pady=2, sticky='we')

def browse_prefix():
    folder = filedialog.askdirectory()
    if folder:
        prefix_entry_var.set(folder)
tk.Button(scrollable_frame, text="Browse...", command=browse_prefix).grid(row=2, column=2, pady=2)

tk.Label(scrollable_frame, text="F2 Directory:").grid(row=3, column=0, sticky='w')
f2_entry_var = tk.StringVar()
f2_entry = tk.Entry(scrollable_frame, width=70, textvariable=f2_entry_var)
f2_entry.grid(row=3, column=1, pady=2, sticky='we')

def browse_f2_dir():
    folder = filedialog.askdirectory()
    if folder:
        f2_entry_var.set(folder)
tk.Button(scrollable_frame, text="Browse...", command=browse_f2_dir).grid(row=3, column=2, pady=2)

tk.Label(scrollable_frame, text="R Installation Folder:").grid(row=4, column=0, sticky='w')
r_folder_entry = tk.Entry(scrollable_frame, width=70)
r_folder_entry.grid(row=4, column=1, pady=2, sticky='we')

def browse_r_folder():
    folder = filedialog.askdirectory()
    if folder:
        r_folder_entry.delete(0, tk.END)
        r_folder_entry.insert(0, folder)
tk.Button(scrollable_frame, text="Browse...", command=browse_r_folder).grid(row=4, column=2, pady=2)

pseudohaploid_var = tk.BooleanVar(value=True)
tk.Checkbutton(scrollable_frame, text="Adjust Pseudohaploid", variable=pseudohaploid_var).grid(row=5, column=0, sticky='w', padx=5)

tk.Button(scrollable_frame, text="Run FST", command=run_fst_analysis, bg="lightblue").grid(row=5, column=1, pady=10, sticky='we')
tk.Button(scrollable_frame, text="Edit and Run R Code", command=edit_and_run_r_code, bg="lightyellow").grid(row=5, column=2, pady=10, sticky='we')

# --- .ind file display and selection ---
ind_frame = tk.LabelFrame(scrollable_frame, text=".ind File Editor", padx=5, pady=5)
ind_frame.grid(row=6, column=0, columnspan=3, sticky='we', padx=5, pady=10)

# Controls: Undo/Redo/Save
editor_controls = tk.Frame(ind_frame)
editor_controls.pack(fill=tk.X)

def undo_ind_changes():
    try: ind_text.edit_undo()
    except: pass

def redo_ind_changes():
    try: ind_text.edit_redo()
    except: pass

def save_ind_file():
    folder_path = prefix_entry_var.get().strip()
    if not folder_path:
        messagebox.showerror("Error", "Dataset folder is empty. Cannot save .ind file.")
        return
    parent_folder = os.path.dirname(folder_path)
    last_folder_name = os.path.basename(folder_path)
    ind_file_name = f"{last_folder_name}.ind"
    ind_path = os.path.join(parent_folder, ind_file_name)
    try:
        content = ind_text.get('1.0', tk.END)
        with open(ind_path, 'w') as f:
            f.write(content)
        status_label.config(text=f".ind file saved: {ind_file_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save .ind file: {str(e)}")

def undo_population_addition():
    global population_history, history_index
    if history_index >= 0:
        entry = population_history[history_index]
        field, old_value = entry['field'], entry['old_value']
        if field == "pop1":
            pop1_entry.delete(0, tk.END)
            pop1_entry.insert(0, old_value)
        elif field == "pop2":
            pop2_entry.delete(0, tk.END)
            pop2_entry.insert(0, old_value)
        history_index -= 1
        status_label.config(text=f"Undo: {field} reverted")

def redo_population_addition():
    global population_history, history_index
    if history_index < len(population_history) - 1:
        history_index += 1
        entry = population_history[history_index]
        field, new_value = entry['field'], entry['new_value']
        if field == "pop1":
            pop1_entry.delete(0, tk.END)
            pop1_entry.insert(0, new_value)
        elif field == "pop2":
            pop2_entry.delete(0, tk.END)
            pop2_entry.insert(0, new_value)
        status_label.config(text=f"Redo: {field} reapplied")


left_controls = tk.Frame(editor_controls)
left_controls.pack(side=tk.LEFT)


tk.Button(left_controls, text="Undo", command=undo_ind_changes).pack(side=tk.LEFT, padx=2)
tk.Button(left_controls, text="Redo", command=redo_ind_changes).pack(side=tk.LEFT, padx=2)
tk.Button(left_controls, text="Save", command=save_ind_file).pack(side=tk.LEFT, padx=2)


# Search bar
search_frame = tk.Frame(ind_frame)
search_frame.pack(fill=tk.X)

search_var = tk.StringVar()
search_entry = tk.Entry(search_frame, textvariable=search_var, width=40)
search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)

# Search buttons
tk.Button(search_frame, text="▲", command=lambda: jump_to_prev_match(), width=2).pack(side=tk.LEFT)
tk.Button(search_frame, text="▼", command=lambda: jump_to_next_match(), width=2).pack(side=tk.LEFT)

# Text editor with scrollbars
text_frame = tk.Frame(ind_frame)
text_frame.pack(fill=tk.BOTH, expand=True)

ind_text = tk.Text(text_frame, wrap=tk.NONE, width=80, height=15, undo=True, autoseparators=True, maxundo=-1)
ind_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

y_scroll = tk.Scrollbar(text_frame, command=ind_text.yview)
y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
ind_text.config(yscrollcommand=y_scroll.set)

x_scroll = tk.Scrollbar(ind_frame, orient=tk.HORIZONTAL, command=ind_text.xview)
x_scroll.pack(fill=tk.X)
ind_text.config(xscrollcommand=x_scroll.set)

# Utility to extract selected population(s)

def save_to_history(field, old_value, new_value):
    global population_history, history_index
    if history_index < len(population_history) - 1:
        population_history = population_history[:history_index + 1]
    population_history.append({
        'field': field,
        'old_value': old_value,
        'new_value': ','.join(new_value) if isinstance(new_value, list) else new_value
    })
    history_index = len(population_history) - 1

def get_selected_populations():
    selected_lines = []
    try:
        sel_start = ind_text.index(tk.SEL_FIRST)
        sel_end = ind_text.index(tk.SEL_LAST)
        selected_text = ind_text.get(sel_start, sel_end)
        selected_lines = selected_text.split('\n')
    except:
        current_line = ind_text.index(tk.INSERT).split('.')[0]
        lines = ind_text.get("1.0", tk.END).split('\n')
        if 0 < int(current_line) <= len(lines):
            selected_lines = [lines[int(current_line)-1]]

    pops = set()
    for line in selected_lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            pops.add(parts[2])
    return sorted(pops)

def save_output_to_file():
    content = output_text.get("1.0", tk.END)
    if not content.strip():
        messagebox.showerror("Error", "No output to save")
        return
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".log",
        filetypes=[("Text Files", "*.log"), ("All Files", "*.*")]
    )
    
    if file_path:
        try:
            # Add encoding='utf-8' here
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            status_label.config(text=f"Output saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

def add_to_pop1():
    global population_history, history_index
    pops = get_selected_populations()
    if pops:
        current = pop1_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("pop1", current, current_pops + new_pops)
            pop1_entry.delete(0, tk.END)
            pop1_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_pop2():
    global population_history, history_index
    pops = get_selected_populations()
    if pops:
        current = pop2_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("pop2", current, current_pops + new_pops)
            pop2_entry.delete(0, tk.END)
            pop2_entry.insert(0, ','.join(current_pops + new_pops))



# Population addition buttons in their own row below
button_frame = tk.Frame(ind_frame)
button_frame.pack(fill=tk.X, pady=(5, 0))

right_controls = tk.Frame(editor_controls)
right_controls.pack(side=tk.RIGHT)


tk.Button(button_frame, text="Add to Pop1", command=add_to_pop1).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Pop2", command=add_to_pop2).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(right_controls, text="Undo Add", command=undo_population_addition).pack(side=tk.LEFT, padx=2)
tk.Button(right_controls, text="Redo Add", command=redo_population_addition).pack(side=tk.LEFT, padx=2)


def load_ind_file():
    folder_path = prefix_entry_var.get().strip()
    if not folder_path:
        return
    parent_folder = os.path.dirname(folder_path)
    last_folder_name = os.path.basename(folder_path)
    ind_path = os.path.join(parent_folder, f"{last_folder_name}.ind")
    if not os.path.isfile(ind_path):
        return
    try:
        with open(ind_path, 'r') as f:
            content = f.read()
        ind_text.delete('1.0', tk.END)
        ind_text.insert(tk.END, content)
        status_label.config(text=f".ind file loaded: {os.path.basename(ind_path)}")
    except Exception as e:
        status_label.config(text=f"Error loading .ind file: {str(e)}")

def on_prefix_change(*args):
    load_ind_file()

prefix_entry_var.trace_add('write', on_prefix_change)

def search_ind_file(*args):
    search_term = search_var.get()
    if not search_term:
        ind_text.tag_remove('highlight', '1.0', tk.END)
        ind_text.tag_remove('current_match', '1.0', tk.END)
        return

    ind_text.tag_remove('highlight', '1.0', tk.END)
    ind_text.tag_remove('current_match', '1.0', tk.END)

    start_pos = '1.0'
    count_var = tk.IntVar()
    matches = []

    while True:
        pos = ind_text.search(search_term, start_pos, stopindex=tk.END, count=count_var, nocase=1)
        if not pos: break
        end_pos = f"{pos}+{count_var.get()}c"
        matches.append((pos, end_pos))
        ind_text.tag_add('highlight', pos, end_pos)
        start_pos = end_pos

    ind_text.tag_config('highlight', background='yellow')
    ind_text.tag_config('current_match', background='orange')

    if hasattr(ind_text, 'search_matches'):
        del ind_text.search_matches
    ind_text.search_matches = matches
    ind_text.current_match = -1
    if matches:
        jump_to_match(0)

def jump_to_match(index):
    if not hasattr(ind_text, 'search_matches'): return
    matches = ind_text.search_matches
    if 0 <= ind_text.current_match < len(matches):
        prev_pos, prev_end = matches[ind_text.current_match]
        ind_text.tag_add('highlight', prev_pos, prev_end)
    ind_text.current_match = index % len(matches)
    pos, end_pos = matches[ind_text.current_match]
    ind_text.tag_add('current_match', pos, end_pos)
    ind_text.mark_set(tk.INSERT, pos)
    ind_text.see(pos)

def jump_to_next_match(event=None):
    if hasattr(ind_text, 'search_matches'):
        jump_to_match(ind_text.current_match + 1)

def jump_to_prev_match(event=None):
    if hasattr(ind_text, 'search_matches'):
        jump_to_match(ind_text.current_match - 1)

search_var.trace_add('write', search_ind_file)
search_entry.bind("<Return>", jump_to_next_match)
search_entry.bind("<Down>", jump_to_next_match)
search_entry.bind("<Up>", jump_to_prev_match)

output_text = scrolledtext.ScrolledText(scrollable_frame, width=150, height=30)
output_text.grid(row=8, column=0, columnspan=3, padx=10, pady=5, sticky='nsew')

# --- Status/Button Row ---
status_button_frame = tk.Frame(scrollable_frame)
status_button_frame.grid(row=9, column=0, columnspan=3, sticky='we', padx=10, pady=(0, 10))

# Status label on left
status_label = tk.Label(status_button_frame, text="Ready.", anchor='w')
status_label.pack(side=tk.LEFT)

# Buttons on right
button_frame = tk.Frame(status_button_frame)
button_frame.pack(side=tk.RIGHT)

# Clear button
clear_button = tk.Button(button_frame, text="Clear", command=clear_output, bg="lightgray", width=10, height=1)
clear_button.pack(side=tk.LEFT, padx=5)

# Add this near the other search functions (around line 1000)
def setup_output_search():
    # Create search frame for output console (placed at bottom)
    output_search_frame = tk.Frame(scrollable_frame)
    output_search_frame.grid(row=7, column=0, columnspan=3, sticky='we', padx=5, pady=(0, 10))
    
    # Left-aligned search components
    search_components = tk.Frame(output_search_frame)
    search_components.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    tk.Label(search_components, text="Output Search:").pack(side=tk.LEFT, padx=(0, 5))
    output_search_var = tk.StringVar()
    output_search_entry = tk.Entry(search_components, textvariable=output_search_var, width=40)
    output_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Search navigation buttons
    output_search_button_frame = tk.Frame(search_components)
    output_search_button_frame.pack(side=tk.LEFT, padx=(5, 0))
    
    tk.Button(output_search_button_frame, text="▲", 
             command=lambda: jump_to_prev_output_match(), width=2).pack(side=tk.LEFT)
    tk.Button(output_search_button_frame, text="▼", 
             command=lambda: jump_to_next_output_match(), width=2).pack(side=tk.LEFT)
    
    # Save button placed to the right of search bar
    save_output_button = tk.Button(button_frame, text="💾 Save", command=save_output_to_file, bg="lightgray", width=10, height=1)
    save_output_button.pack(side=tk.LEFT)


    def search_output(*args):
        search_term = output_search_var.get()
        if not search_term:
            output_text.tag_remove('output_highlight', '1.0', tk.END)
            output_text.tag_remove('output_current_match', '1.0', tk.END)
            return
        
        output_text.tag_remove('output_highlight', '1.0', tk.END)
        output_text.tag_remove('output_current_match', '1.0', tk.END)
        
        start_pos = '1.0'
        count_var = tk.IntVar()
        matches = []
        
        while True:
            pos = output_text.search(search_term, start_pos, stopindex=tk.END, count=count_var, nocase=1)
            if not pos: break
            end_pos = f"{pos}+{count_var.get()}c"
            matches.append((pos, end_pos))
            output_text.tag_add('output_highlight', pos, end_pos)
            start_pos = end_pos
        
        output_text.tag_config('output_highlight', background='yellow', foreground='black')
        output_text.tag_config('output_current_match', background='orange', foreground='black')
        
        if hasattr(output_text, 'output_search_matches'):
            del output_text.output_search_matches
        output_text.output_search_matches = matches
        output_text.output_current_match = -1
        
        if matches:
            jump_to_output_match(0)

    def jump_to_output_match(index):
        if not hasattr(output_text, 'output_search_matches') or not output_text.output_search_matches:
            return
        
        matches = output_text.output_search_matches
        if 0 <= output_text.output_current_match < len(matches):
            prev_pos, prev_end = matches[output_text.output_current_match]
            output_text.tag_add('output_highlight', prev_pos, prev_end)
        
        output_text.output_current_match = index % len(matches)
        pos, end_pos = matches[output_text.output_current_match]
        
        output_text.tag_add('output_current_match', pos, end_pos)
        output_text.mark_set(tk.INSERT, pos)
        output_text.see(pos)

    def jump_to_next_output_match(event=None):
        if hasattr(output_text, 'output_search_matches') and output_text.output_search_matches:
            jump_to_output_match(output_text.output_current_match + 1)

    def jump_to_prev_output_match(event=None):
        if hasattr(output_text, 'output_search_matches') and output_text.output_search_matches:
            jump_to_output_match(output_text.output_current_match - 1)

    output_search_var.trace_add('write', search_output)
    output_search_entry.bind("<Return>", jump_to_next_output_match)
    output_search_entry.bind("<Down>", jump_to_next_output_match)
    output_search_entry.bind("<Up>", jump_to_prev_output_match)
    
# Call this function after creating the output_text widget
setup_output_search()

# Make columns expandable
scrollable_frame.grid_columnconfigure(1, weight=1)
scrollable_frame.grid_rowconfigure(7, weight=1)

# --- Repeating Vertical Text Label on the Right ---
word = 'pepsimanfire'
repeat_count = 5  # You can increase this to make it go further down
vertical_text = '\n'.join(list(word) * repeat_count)

vertical_label = tk.Label(scrollable_frame, text=vertical_text, font=("Helvetica", 12, "bold"), fg="gray")
vertical_label.grid(row=0, column=5, rowspan=999, sticky='ns', padx=(0, 5), pady=10)

root.mainloop()
