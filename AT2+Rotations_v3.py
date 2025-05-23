import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import tempfile
import os
import re
from datetime import datetime
from itertools import combinations

population_history = []
history_index = -1

# Add the clear_output function
def clear_output():
    output_text.delete('1.0', tk.END)

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

def undo_population_addition():
    global history_index
    if history_index >= 0:
        entry = population_history[history_index]
        field, old_value = entry['field'], entry['old_value']
        field_map = {
            'target': target_entry,
            'left': left_entry,
            'right': right_entry,
            'fixed_right': fixed_right_entry,
            'fixed_left': fixed_left_entry,
            'rotation_pool': rotation_pool_entry
        }
        if field in field_map:
            field_map[field].delete(0, tk.END)
            field_map[field].insert(0, old_value)
            status_label.config(text=f"Undo: reverted {field}")
        history_index -= 1
    else:
        status_label.config(text="Nothing to undo")

def redo_population_addition():
    global history_index
    if history_index < len(population_history) - 1:
        history_index += 1
        entry = population_history[history_index]
        field, new_value = entry['field'], entry['new_value']
        field_map = {
            'target': target_entry,
            'left': left_entry,
            'right': right_entry,
            'fixed_right': fixed_right_entry,
            'fixed_left': fixed_left_entry,
            'rotation_pool': rotation_pool_entry
        }
        if field in field_map:
            field_map[field].delete(0, tk.END)
            field_map[field].insert(0, new_value)
            status_label.config(text=f"Redo: reapplied {field}")
    else:
        status_label.config(text="Nothing to redo")


def add_to_target():
    pops = get_selected_populations()
    if pops:
        current = target_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("target", current, current_pops + new_pops)
            target_entry.delete(0, tk.END)
            target_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_left():
    pops = get_selected_populations()
    if pops:
        current = left_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("left", current, current_pops + new_pops)
            left_entry.delete(0, tk.END)
            left_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_right():
    pops = get_selected_populations()
    if pops:
        current = right_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("right", current, current_pops + new_pops)
            right_entry.delete(0, tk.END)
            right_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_fixed_right():
    pops = get_selected_populations()
    if pops:
        current = fixed_right_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("fixed_right", current, current_pops + new_pops)
            fixed_right_entry.delete(0, tk.END)
            fixed_right_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_fixed_left():
    pops = get_selected_populations()
    if pops:
        current = fixed_left_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("fixed_left", current, current_pops + new_pops)
            fixed_left_entry.delete(0, tk.END)
            fixed_left_entry.insert(0, ','.join(current_pops + new_pops))

def add_to_rotation_pool():
    pops = get_selected_populations()
    if pops:
        current = rotation_pool_entry.get().strip()
        current_pops = [p.strip() for p in re.split(r'[,\s]+', current) if p.strip()]
        new_pops = [p for p in pops if p not in current_pops]
        if new_pops:
            save_to_history("rotation_pool", current, current_pops + new_pops)
            rotation_pool_entry.delete(0, tk.END)
            rotation_pool_entry.insert(0, ','.join(current_pops + new_pops))

# FORMAT POPS FUNCTION
def format_pops(input_str):
    clean_input = input_str.replace('"', '').replace("'", '').replace(',', ' ')
    pops = [p.strip() for p in clean_input.split() if p.strip()]
    return ','.join(f'"{p}"' for p in pops)

# GET R LIBRARY PATHS
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
    except Exception as e:
        return []

# CHECK IF PACKAGE EXISTS IN ANY OF THE R LIBRARY PATHS
def check_package_in_paths(package_name, paths):
    for path in paths:
        if os.path.isdir(os.path.join(path, package_name)):
            return path
    return None

# Persistent variable to store modified R code
custom_r_code = None

# MAIN RUN FUNCTION
def run_qpadm():
    target_pops_raw = target_entry.get()
    left_pops_raw = left_entry.get()
    right_pops_raw = right_entry.get()
    dataset_prefix = prefix_entry.get()
    r_folder = r_folder_entry.get().strip()

    if not (target_pops_raw and left_pops_raw and right_pops_raw and dataset_prefix):
        messagebox.showerror("Missing info", "Please fill in all fields.")
        return

    if not r_folder:
        messagebox.showerror("Missing R folder", "Please specify the R installation folder.")
        return

    rscript_path = os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')
    if not os.path.isfile(rscript_path):
        messagebox.showerror(
            "Rscript not found",
            f"Rscript.exe not found at expected location:\n{rscript_path}"
        )
        return

    target_pops = format_pops(target_pops_raw)
    left_pops = format_pops(left_pops_raw)
    right_pops = format_pops(right_pops_raw)

    r_lib_paths = get_r_library_paths(rscript_path)
    package_path = check_package_in_paths("admixtools", r_lib_paths)
    lib_path_code = f'.libPaths("{package_path}")\n' if package_path else ''

    r_code = f"""
{lib_path_code}
library(admixtools)
library(tidyverse)

prefix = "{dataset_prefix}"
target = c({target_pops})
left = c({left_pops})
right = c({right_pops})

results = qpadm(prefix, left, right, target, allsnps = TRUE)

cat("\\nRESULTS_WEIGHTS\\n")
print(results$weights)
cat("\\nRESULTS_POPDROP\\n")
print(results$popdrop)
cat("\\nRESULTS_SUMMARY\\n")
cat("Blocks:", results$summary$nblocks, "SNPs:", results$summary$nsnps, "\\n")
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

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_text.insert(tk.END, f"\n---\nDone by pepsimanfire - Run started at {timestamp}\n")
        output_text.insert(tk.END, f"Target: {target_pops_raw}\nLeft: {left_pops_raw}\nRight: {right_pops_raw}\n\n")
        output_text.see(tk.END)
        output_text.update()

        full_output = []
        weights_output = ""
        popdrop_output = ""
        summary_output = ""
        capturing_weights = False
        capturing_popdrop = False
        capturing_summary = False

        snps_count = None
        blocks_total = None

        for raw_line in process.stdout:
            line = raw_line.strip()
            full_output.append(raw_line)

            if "RESULTS_WEIGHTS" in line:
                capturing_weights = True
                capturing_popdrop = capturing_summary = False
                continue
            elif "RESULTS_POPDROP" in line:
                capturing_popdrop = True
                capturing_weights = capturing_summary = False
                continue
            elif "RESULTS_SUMMARY" in line:
                capturing_summary = True
                capturing_weights = capturing_popdrop = False
                continue

            if capturing_weights:
                weights_output += line + "\n"
                continue
            elif capturing_popdrop:
                popdrop_output += line + "\n"
                continue
            elif capturing_summary:
                if re.match(r'^Blocks:\s*SNPs:\s*$', line):
                    continue
                summary_output += line + "\n"
                continue

            snps_match = re.search(r'Computing block lengths for (\d+) SNPs', line)
            if snps_match:
                snps_count = snps_match.group(1)

            block_match = re.search(r'Computing .* block (\d+) out of (\d+)', line)
            if block_match:
                block_num, total_blocks = block_match.groups()
                blocks_total = total_blocks
                status_label.config(text=f"Computing block {block_num} of {total_blocks}...")
                status_label.update()

            if "Error" in line or "error" in line:
                output_text.insert(tk.END, f"❌ {line}\n")
                output_text.see(tk.END)
                output_text.update()

        process.wait()

        if process.returncode != 0:
            error_message = '\n'.join(full_output)
            output_text.insert(tk.END, f"\n❌ qpAdm failed with exit code {process.returncode}:\n{error_message}\n")
            output_text.see(tk.END)
        else:
            output_text.insert(tk.END, "Weights:\n" + weights_output)
            output_text.insert(tk.END, "Popdrop:\n" + popdrop_output)
            if summary_output:
                output_text.insert(tk.END, summary_output)
            if blocks_total and snps_count:
                output_text.insert(tk.END, f"Total: {blocks_total} Blocks, {snps_count} SNPs\n")

        output_text.see(tk.END)
        output_text.update()
        status_label.config(text="qpAdm completed." if process.returncode == 0 else "qpAdm failed!")

    except Exception as e:
        messagebox.showerror("Error running R", str(e))

    finally:
        os.remove(r_script_path)

def edit_and_run_r_code():
    global custom_r_code

    dataset_prefix = prefix_entry.get().strip()
    r_folder = r_folder_entry.get().strip()

    if not r_folder:
        messagebox.showerror("Missing R folder", "Please specify the R installation folder.")
        return

    rscript_path = os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')
    if not os.path.isfile(rscript_path):
        messagebox.showerror("Rscript not found", f"Rscript.exe not found at:\n{rscript_path}")
        return

    # Default R code template
    r_lib_paths = get_r_library_paths(rscript_path)
    package_path = check_package_in_paths("admixtools", r_lib_paths)
    lib_path_code = f'.libPaths("{package_path}")\n' if package_path else ''

    default_r_code = f"""
{lib_path_code}
library(admixtools)
library(tidyverse)

# You must edit these:
prefix = "{dataset_prefix}" # <- If your dataset name is john_merged and your folder is john/dataset, put it like this: john/dataset/john_merged
target = c("POP1")  # <- Replace with your actual target populations
left = c("LEFT1", "LEFT2")  # <- Replace with your left populations
right = c("RIGHT1", "RIGHT2")  # <- Replace with your right populations

results = qpadm(prefix, left, right, target, allsnps = TRUE)

cat("\\nRESULTS_WEIGHTS\\n")
print(results$weights)
cat("\\nRESULTS_POPDROP\\n")
print(results$popdrop)
cat("\\nRESULTS_SUMMARY\\n")
cat("Blocks:", results$summary$nblocks, "SNPs:", results$summary$nsnps, "\\n")
""".strip()

    if custom_r_code is None:
        custom_r_code = default_r_code  # first-time setup

    # --- Create the popup editor window ---
    editor_win = tk.Toplevel(root)
    editor_win.attributes('-topmost', True)
    editor_win.title("Edit R Code Manually")

    def enforce_always_on_top():
        try:
            editor_win.attributes("-topmost", True)
        except tk.TclError:
            return  # Window likely closed
        editor_win.after(1000, enforce_always_on_top)

    enforce_always_on_top()  # Start the loop
    
    # Text editor
    text_editor = tk.Text(editor_win, wrap=tk.NONE, width=100, height=30, undo=True)
    text_editor.insert('1.0', custom_r_code)
    text_editor.pack(fill=tk.BOTH, expand=True)
    text_editor.bind('<Control-z>', lambda e: output_text.edit_undo())

    # --- Button actions ---
    def run_edited_r_code():
        global custom_r_code
        edited_code = text_editor.get("1.0", tk.END)
        custom_r_code = edited_code  # Save persistently

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
            output_text.insert(tk.END, f"\n---\n[Done by pepsimanfire - Custom R Code Output - {timestamp}]\n")

            full_output = []
            for line in process.stdout:
                output_text.insert(tk.END, line)
                full_output.append(line)
                output_text.see(tk.END)
            
            process.wait()
            
            if process.returncode != 0:
                error_message = ''.join(full_output)
                output_text.insert(tk.END, f"\n❌ Custom R code failed (exit code {process.returncode}):\n{error_message}\n")
                output_text.see(tk.END)
                status_label.config(text="Custom R code failed!")
            else:
                status_label.config(text="Custom R code executed.")

        except Exception as e:
            messagebox.showerror("Execution Error", str(e))
        finally:
            os.remove(r_script_path)

    def restore_original_code():
        nonlocal text_editor
        global custom_r_code
        text_editor.delete("1.0", tk.END)
        text_editor.insert("1.0", default_r_code)
        status_label.config(text="Original code restored. Remember to save if you want to keep this version.")

    def on_editor_close():
        current_code = text_editor.get("1.0", tk.END)
    # Always save the edited code before closing
        global custom_r_code
        custom_r_code = current_code
        editor_win.destroy()

    editor_win.protocol("WM_DELETE_WINDOW", on_editor_close)

    # --- Buttons Frame ---
    button_frame = tk.Frame(editor_win)
    button_frame.pack(fill=tk.X, pady=5)

    restore_btn = tk.Button(button_frame, text="Restore Original Code", command=restore_original_code, bg="orange")
    restore_btn.pack(side=tk.LEFT, padx=5)

    run_button = tk.Button(editor_win, text="Run This Code", command=run_edited_r_code, bg="lightgreen")
    run_button.pack(pady=5)

# --- ROTATION FUNCTIONS ---
def run_rotation():
    # --- Get Rscript path first ---
    r_folder = r_folder_entry.get().strip()
    if not r_folder:
        messagebox.showerror("Error", "Please specify the R installation folder")
        return

    # Try both possible Rscript paths
    rscript_path = os.path.join(r_folder, 'bin', 'Rscript.exe')
    if not os.path.isfile(rscript_path):
        rscript_path = os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')
        if not os.path.isfile(rscript_path):
            messagebox.showerror("Error", f"Rscript.exe not found at:\n{os.path.join(r_folder, 'bin', 'Rscript.exe')}\nor\n{os.path.join(r_folder, 'bin', 'x64', 'Rscript.exe')}")
            return

    # --- Get Inputs ---
    target_pops = target_entry.get().strip()
    fixed_left = fixed_left_entry.get().strip()
    fixed_right = fixed_right_entry.get().strip()
    rotation_pool = rotation_pool_entry.get().strip()
    model_min = int(model_min_entry.get())
    model_max = int(model_max_entry.get())
    prefix = prefix_entry.get().strip()
    rotation_mode = rotation_mode_entry.get().strip().lower()[0] if rotation_mode_entry.get().strip() else 'd'

    # Format populations
    def format_pop_list(pop_str):
        if not pop_str:
            return []
        pops = [p.strip().strip('"') for p in pop_str.split(',')]
        return [f'"{p}"' for p in pops if p]

    fixed_left_pops = format_pop_list(fixed_left)
    fixed_right_pops = format_pop_list(fixed_right)
    rotation_pool_pops = format_pop_list(rotation_pool)

    # --- Generate all models based on rotation mode ---
    all_models = []
    
    if rotation_mode == "r":
        # RIGHT-ONLY: Rotation pool only added to right (left stays fixed)
        for size in range(model_min, model_max + 1):
            for combo in combinations(rotation_pool_pops, size):
                right = fixed_right_pops + list(combo)
                left = fixed_left_pops  # Left remains unchanged
                if not (set(left) & set(right)):  # Skip if overlap
                    all_models.append((left, right))
                    
    elif rotation_mode == "l":
        # LEFT-ONLY: Rotation pool only added to left (right stays fixed)
        for size in range(model_min, model_max + 1):
            for combo in combinations(rotation_pool_pops, size):
                left = fixed_left_pops + list(combo)
                right = fixed_right_pops  # Right remains unchanged
                if not (set(left) & set(right)):  # Skip if overlap
                    all_models.append((left, right))
    else:
        # DEFAULT: Original behavior - rotate both sides
        for size in range(model_min, model_max + 1):
            for combo in combinations(rotation_pool_pops, size):
                rotating_left = list(combo)
                rotating_right = [p for p in rotation_pool_pops if p not in rotating_left]
                left = fixed_left_pops + rotating_left
                right = fixed_right_pops + rotating_right
                if not (set(left) & set(right)):  # Skip if overlap
                    all_models.append((left, right))
    
    # Remove duplicates
    unique_models = []
    seen = set()
    for left, right in all_models:
        key = (tuple(sorted(left)), tuple(sorted(right)))
        if key not in seen:
            seen.add(key)
            unique_models.append((left, right))
    
    # Print all models first
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_text.insert(tk.END, f"\n---\n[Rotation Analysis - {timestamp}]\n")
    output_text.insert(tk.END, f"Target: {target_pops}\n")
    output_text.insert(tk.END, f"Fixed Left: {fixed_left_pops}\n")
    output_text.insert(tk.END, f"Fixed Right: {fixed_right_pops}\n")
    output_text.insert(tk.END, f"Rotation Pool: {rotation_pool_pops}\n")
    output_text.insert(tk.END, f"Rotation Mode: {'Right-only' if rotation_mode == 'r' else 'Left-only' if rotation_mode == 'l' else 'Default'}\n")
    output_text.insert(tk.END, f"Model Size Range: {model_min}-{model_max}\n")
    output_text.insert(tk.END, f"Total Models: {len(unique_models)}\n\n")
    output_text.see(tk.END)
    output_text.update()

    # --- Run Models ---
    total_models = len(unique_models)
    for idx, (left, right) in enumerate(unique_models):
        current_model = idx + 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_text.insert(tk.END, f"\n---\n[Model {current_model}/{total_models} - {timestamp}]\n")
        output_text.insert(tk.END, f"Left: {', '.join(left)}\n")
        output_text.insert(tk.END, f"Right: {', '.join(right)}\n")
        output_text.update()

        # Format populations for R
        formatted_left = ','.join(left)
        formatted_right = ','.join(right)
        formatted_target = f'"{target_pops}"'

        # Generate R code with same output format as run_qpadm()
        r_code = f"""
library(admixtools)
library(tidyverse)

prefix <- "{prefix}"
target <- c({formatted_target})
left <- c({formatted_left})
right <- c({formatted_right})

tryCatch({{
    results <- qpadm(prefix, left, right, target, allsnps = TRUE)
    
    cat("\\nRESULTS_WEIGHTS\\n")
    print(results$weights)
    cat("\\nRESULTS_POPDROP\\n")
    print(results$popdrop)
}}, error = function(e) {{
    cat("ERROR:", e$message, "\\n")
}})
"""

        with tempfile.NamedTemporaryFile(delete=False, suffix=".R", mode='w') as r_script:
            r_script.write(r_code)
            r_script_path = r_script.name

        try:
            process = subprocess.Popen(
                [rscript_path, r_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            # Parse output the same way as run_qpadm()
            full_output = []
            weights_output = ""
            popdrop_output = ""
            summary_output = ""
            capturing_weights = False
            capturing_popdrop = False
            capturing_summary = False

            for raw_line in process.stdout:
                line = raw_line.strip()
                full_output.append(raw_line)

                if "RESULTS_WEIGHTS" in line:
                    capturing_weights = True
                    capturing_popdrop = capturing_summary = False
                    continue
                elif "RESULTS_POPDROP" in line:
                    capturing_popdrop = True
                    capturing_weights = capturing_summary = False
                    continue
                elif "RESULTS_SUMMARY" in line:
                    capturing_summary = True
                    capturing_weights = capturing_popdrop = False
                    continue

                if capturing_weights:
                    weights_output += line + "\n"
                elif capturing_popdrop:
                    popdrop_output += line + "\n"
                elif capturing_summary:
                    summary_output += line + "\n"

                # Show progress for long-running models
                block_match = re.search(r'Computing .* block (\d+) out of (\d+)', line)
                if block_match:
                    block_num, total_blocks = block_match.groups()
                    status_label.config(text=f"Model {current_model}/{total_models} - Block {block_num}/{total_blocks}")
                    status_label.update()

            process.wait()

            # Display results or errors
            if process.returncode != 0:
                error_message = '\n'.join(full_output)
                output_text.insert(tk.END, f"❌ Model {current_model} failed (exit code {process.returncode}):\n{error_message}\n")
            else:
                if weights_output:
                    output_text.insert(tk.END, "Weights:\n" + weights_output + "\n")
                if popdrop_output:
                    output_text.insert(tk.END, "Popdrop:\n" + popdrop_output + "\n")
                if summary_output:
                    output_text.insert(tk.END, "Summary:\n" + summary_output + "\n")

            output_text.see(tk.END)
            output_text.update()

        except Exception as e:
            output_text.insert(tk.END, f"❌ Model {current_model} failed: {str(e)}\n")
            output_text.see(tk.END)

        finally:
            if os.path.exists(r_script_path):
                os.remove(r_script_path)

    status_label.config(text="Rotation analysis completed!")
    
# --- MAIN WINDOW SETUP ---
root = tk.Tk()
root.title("qpAdm Runner")

# --- Scrollable Window Setup ---
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
tk.Label(scrollable_frame, text="Target populations:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
target_entry = tk.Entry(scrollable_frame, width=70)
target_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky='we')

tk.Label(scrollable_frame, text="Left populations:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
left_var = tk.StringVar()
left_entry = tk.Entry(scrollable_frame, width=70)
left_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky='we')

def open_left_editor():
    top = tk.Toplevel(root)
    top.title("Edit Left Populations - Large View")
    top.geometry("800x400")
    top.resizable(True, True)

    # Keep the window on top permanently
    top.attributes("-topmost", True)

    def keep_on_top():
        top.attributes("-topmost", True)  # Reapply the attribute
        top.after(1000, keep_on_top)  # Repeat every second

    keep_on_top()  # Start the loop

    text = tk.Text(top, wrap=tk.WORD, font=("Consolas", 12))
    text.pack(expand=True, fill="both")
    text.insert("1.0", left_var.get())

    syncing_from_popup = False
    syncing_from_main = False

    def sync_popup_to_entry(event=None):
        nonlocal syncing_from_popup
        syncing_from_popup = True
        left_var.set(text.get("1.0", "end-1c"))
        syncing_from_popup = False

    def sync_entry_to_popup(*args):
        nonlocal syncing_from_main
        if not syncing_from_popup:
            syncing_from_main = True
            value = left_var.get()
            if value != text.get("1.0", "end-1c"):
                text.delete("1.0", tk.END)
                text.insert("1.0", value)
            syncing_from_main = False

    text.bind("<KeyRelease>", sync_popup_to_entry)
    trace_id = left_var.trace_add("write", sync_entry_to_popup)

    def on_close():
        left_var.trace_remove("write", trace_id)
        top.destroy()

    tk.Button(top, text="Close", command=on_close).pack(pady=5)


tk.Button(scrollable_frame, text="🡕", width=3, command=open_left_editor).grid(row=1, column=3, padx=(0, 5))

tk.Label(scrollable_frame, text="Right populations:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
right_var = tk.StringVar()  # <-- Corrected to right_var
right_entry = tk.Entry(scrollable_frame, width=70, textvariable=right_var)  # <-- Corrected to right_entry
right_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=2, sticky='we')  # <-- Corrected to right_entry

def open_right_editor():
    top = tk.Toplevel(root)
    top.title("Edit Right Populations - Large View")
    top.geometry("800x400")
    top.resizable(True, True)

    # Keep the window on top permanently
    top.attributes("-topmost", True)

    def keep_on_top():
        top.attributes("-topmost", True)  # Reapply the attribute
        top.after(1000, keep_on_top)  # Repeat every second

    keep_on_top()  # Start the loop

    text = tk.Text(top, wrap=tk.WORD, font=("Consolas", 12))
    text.pack(expand=True, fill="both")
    text.insert("1.0", right_var.get())

    syncing_from_popup = False
    syncing_from_main = False

    def sync_popup_to_entry(event=None):
        nonlocal syncing_from_popup
        syncing_from_popup = True
        right_var.set(text.get("1.0", "end-1c"))
        syncing_from_popup = False

    def sync_entry_to_popup(*args):
        nonlocal syncing_from_main
        if not syncing_from_popup:
            syncing_from_main = True
            value = right_var.get()
            if value != text.get("1.0", "end-1c"):
                text.delete("1.0", tk.END)
                text.insert("1.0", value)
            syncing_from_main = False

    text.bind("<KeyRelease>", sync_popup_to_entry)
    trace_id = right_var.trace_add("write", sync_entry_to_popup)

    def on_close():
        right_var.trace_remove("write", trace_id)
        top.destroy()

    tk.Button(top, text="Close", command=on_close).pack(pady=5)

tk.Button(scrollable_frame, text="🡕", width=3, command=open_right_editor).grid(row=2, column=3, padx=(0, 5))

tk.Label(scrollable_frame, text="Dataset prefix (path):").grid(row=3, column=0, sticky='w', padx=5, pady=2)
prefix_entry_var = tk.StringVar()
prefix_entry = tk.Entry(scrollable_frame, width=70, textvariable=prefix_entry_var)
prefix_entry.grid(row=3, column=1, padx=5, pady=2, sticky='we')

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        prefix_entry_var.set(folder_selected)

tk.Button(scrollable_frame, text="Browse...", command=browse_folder).grid(row=3, column=2, padx=5, pady=2)

# R Installation Folder
tk.Label(scrollable_frame, text="R Installation Folder:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
r_folder_entry = tk.Entry(scrollable_frame, width=70)
r_folder_entry.grid(row=4, column=1, padx=5, pady=2, sticky='we')

def browse_r_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        r_folder_entry.delete(0, tk.END)
        r_folder_entry.insert(0, folder_selected)

tk.Button(scrollable_frame, text="Browse...", command=browse_r_folder).grid(row=4, column=2, padx=5, pady=2)

# --- .ind FILE EDITOR ---
ind_frame = tk.LabelFrame(scrollable_frame, text=".ind File Editor", padx=5, pady=5)
ind_frame.grid(row=5, column=0, columnspan=3, sticky='we', padx=5, pady=10)

# Editor controls
editor_controls = tk.Frame(ind_frame)
editor_controls.pack(fill=tk.X, pady=(0, 5))

left_controls = tk.Frame(editor_controls)
left_controls.pack(side=tk.LEFT)

right_controls = tk.Frame(editor_controls)
right_controls.pack(side=tk.RIGHT)

tk.Button(right_controls, text="Undo Add", command=undo_population_addition).pack(side=tk.LEFT, padx=2)
tk.Button(right_controls, text="Redo Add", command=redo_population_addition).pack(side=tk.LEFT, padx=2)

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

tk.Button(editor_controls, text="Undo", command=undo_ind_changes).pack(side=tk.LEFT, padx=2)
tk.Button(editor_controls, text="Redo", command=redo_ind_changes).pack(side=tk.LEFT, padx=2)
tk.Button(editor_controls, text="Save", command=save_ind_file).pack(side=tk.LEFT, padx=2)

# Search functionality
search_frame = tk.Frame(ind_frame)
search_frame.pack(fill=tk.X, pady=(0, 5))

tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
search_var = tk.StringVar()
search_entry = tk.Entry(search_frame, textvariable=search_var, width=40)
search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

search_button_frame = tk.Frame(search_frame)
search_button_frame.pack(side=tk.LEFT, padx=(5, 0))

tk.Button(search_button_frame, text="▲", command=lambda: jump_to_prev_match(), width=2).pack(side=tk.LEFT)
tk.Button(search_button_frame, text="▼", command=lambda: jump_to_next_match(), width=2).pack(side=tk.LEFT)

# Text widget with scrollbars
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

# Population selection buttons
button_frame = tk.Frame(ind_frame)
button_frame.pack(fill=tk.X, pady=(5, 0))

def get_selected_populations():
    try:
        sel_start = ind_text.index(tk.SEL_FIRST)
        sel_end = ind_text.index(tk.SEL_LAST)
        selected_text = ind_text.get(sel_start, sel_end)
        selected_lines = selected_text.split('\n')
    except:
        current_line = ind_text.index(tk.INSERT).split('.')[0]
        selected_lines = [ind_text.get(f"{current_line}.0", f"{current_line}.end")]
    
    pops = set()
    for line in selected_lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            pops.add(parts[2])
    return sorted(pops)

tk.Button(button_frame, text="Add to Target", command=add_to_target).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Left", command=add_to_left).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Right", command=add_to_right).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Fixed References", command=add_to_fixed_right).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Fixed Sources", command=add_to_fixed_left).pack(side=tk.LEFT, padx=5, expand=True)
tk.Button(button_frame, text="Add to Rotational Pool", command=add_to_rotation_pool).pack(side=tk.LEFT, padx=5, expand=True)

def load_ind_file():
    folder_path = prefix_entry_var.get().strip()
    if not folder_path:
        status_label.config(text="Dataset folder is empty. No .ind file loaded.")
        return

    parent_folder = os.path.dirname(folder_path)
    last_folder_name = os.path.basename(folder_path)
    ind_file_name = f"{last_folder_name}.ind"
    ind_path = os.path.join(parent_folder, ind_file_name)

    if not os.path.isfile(ind_path):
        status_label.config(text=f"No .ind file named '{ind_file_name}' found in parent folder.")
        return

    try:
        with open(ind_path, 'r') as f:
            content = f.read()
        ind_text.delete('1.0', tk.END)
        ind_text.insert(tk.END, content)
        status_label.config(text=f".ind file loaded: {ind_file_name}")
    except Exception as e:
        status_label.config(text=f"Error loading .ind file: {str(e)}")

def on_prefix_change(*args):
    load_ind_file()

prefix_entry_var.trace_add('write', on_prefix_change)

# Search functions
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
    
    ind_text.tag_config('highlight', background='yellow', foreground='black')
    ind_text.tag_config('current_match', background='orange', foreground='black')
    
    if hasattr(ind_text, 'search_matches'):
        del ind_text.search_matches
    ind_text.search_matches = matches
    ind_text.current_match = -1
    
    if matches:
        jump_to_match(0)

def jump_to_match(index):
    if not hasattr(ind_text, 'search_matches') or not ind_text.search_matches:
        return
    
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
    if hasattr(ind_text, 'search_matches') and ind_text.search_matches:
        jump_to_match(ind_text.current_match + 1)

def jump_to_prev_match(event=None):
    if hasattr(ind_text, 'search_matches') and ind_text.search_matches:
        jump_to_match(ind_text.current_match - 1)

search_var.trace_add('write', search_ind_file)
search_entry.bind("<Return>", jump_to_next_match)
search_entry.bind("<Down>", jump_to_next_match)
search_entry.bind("<Up>", jump_to_prev_match)

fixed_left_var = tk.StringVar()
fixed_right_var = tk.StringVar()
rotation_pool_var = tk.StringVar()

# Add this near the other search functions (around line 1000)
def setup_output_search():
    # Create search frame for output console
    output_search_frame = tk.Frame(scrollable_frame)
    output_search_frame.grid(row=9, column=0, columnspan=3, sticky='we', padx=5, pady=2)

    tk.Label(output_search_frame, text="Output Search:").pack(side=tk.LEFT, padx=(0, 5))
    output_search_var = tk.StringVar()
    output_search_entry = tk.Entry(output_search_frame, textvariable=output_search_var, width=40)
    output_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    output_search_button_frame = tk.Frame(output_search_frame)
    output_search_button_frame.pack(side=tk.LEFT, padx=(5, 0))

    tk.Button(output_search_button_frame, text="▲", command=lambda: jump_to_prev_output_match(), width=2).pack(side=tk.LEFT)
    tk.Button(output_search_button_frame, text="▼", command=lambda: jump_to_next_output_match(), width=2).pack(side=tk.LEFT)

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

# --- ROTATION PARAMETERS ---
rotation_frame = tk.LabelFrame(scrollable_frame, text="qpAdm Rotation Parameters", padx=5, pady=5)
rotation_frame.grid(row=6, column=0, columnspan=3, sticky='we', padx=5, pady=10)

tk.Label(rotation_frame, text="Fixed References (Right):").grid(row=0, column=0, sticky='w', padx=5)
fixed_right_entry = tk.Entry(rotation_frame, width=150, textvariable=fixed_right_var)
fixed_right_entry.grid(row=0, column=1, padx=5)

tk.Label(rotation_frame, text="Fixed Sources (Left - Optional):").grid(row=1, column=0, sticky='w', padx=5)
fixed_left_entry = tk.Entry(rotation_frame, width=150, textvariable=fixed_left_var)
fixed_left_entry.grid(row=1, column=1, padx=5)

tk.Label(rotation_frame, text="Rotational Pool:").grid(row=2, column=0, sticky='w', padx=5)
rotation_pool_entry = tk.Entry(rotation_frame, width=150, textvariable=rotation_pool_var)
rotation_pool_entry.grid(row=2, column=1, padx=5)

# Editor functions for each field
def open_fixed_left_editor():
    create_synced_editor(
        title="Edit Fixed Left Populations",
        textvariable=fixed_left_var,
        entry_widget=fixed_left_entry
    )

def open_fixed_right_editor():
    create_synced_editor(
        title="Edit Fixed Right Populations",
        textvariable=fixed_right_var,
        entry_widget=fixed_right_entry
    )

def open_rotation_pool_editor():
    create_synced_editor(
        title="Edit Rotation Pool Populations",
        textvariable=rotation_pool_var,
        entry_widget=rotation_pool_entry
    )

# Generic editor creation function
def create_synced_editor(title, textvariable, entry_widget):
    top = tk.Toplevel(root)
    top.title(title)
    top.geometry("800x400")
    top.resizable(True, True)

    # Keep window on top
    def keep_on_top():
        top.attributes("-topmost", True)
        top.after(1000, keep_on_top)
    keep_on_top()

    text = tk.Text(top, wrap=tk.WORD, font=("Consolas", 12))
    text.pack(expand=True, fill="both")
    text.insert("1.0", textvariable.get())

    # Synchronization variables
    syncing_from_popup = False
    syncing_from_main = False

    # Pop-up → Main Entry sync
    def sync_popup_to_entry(event=None):
        nonlocal syncing_from_popup
        syncing_from_popup = True
        textvariable.set(text.get("1.0", "end-1c"))
        syncing_from_popup = False

    # Main Entry → Pop-up sync
    def sync_entry_to_popup(*args):
        nonlocal syncing_from_main
        if not syncing_from_popup:
            syncing_from_main = True
            current_value = textvariable.get()
            if current_value != text.get("1.0", "end-1c"):
                text.delete("1.0", tk.END)
                text.insert("1.0", current_value)
            syncing_from_main = False

    # Set up event bindings
    text.bind("<KeyRelease>", sync_popup_to_entry)
    trace_id = textvariable.trace_add("write", sync_entry_to_popup)

    # Close handler
    def on_close():
        textvariable.trace_remove("write", trace_id)
        top.destroy()

    # Close button
    tk.Button(top, text="Close", command=on_close).pack(pady=5)
    top.protocol("WM_DELETE_WINDOW", on_close)


# Add buttons next to the rotation parameters entries
def create_editor_button(parent, row, column, command):
    btn = tk.Button(parent, text="🡕", width=3, command=command)
    btn.grid(row=row, column=column, padx=(0, 5))
    return btn

# Fixed Left Editor
create_editor_button(rotation_frame, 1, 2, open_fixed_left_editor)
# Fixed Right Editor
create_editor_button(rotation_frame, 0, 2, open_fixed_right_editor)
# Rotation Pool Editor
create_editor_button(rotation_frame, 2, 2, open_rotation_pool_editor)


tk.Label(rotation_frame, text="Model Size (min-max):").grid(row=3, column=0, sticky='w', padx=5)
model_min_entry = tk.Entry(rotation_frame, width=5)
model_min_entry.grid(row=3, column=1, sticky='w', padx=5)
model_max_entry = tk.Entry(rotation_frame, width=5)
model_max_entry.grid(row=3, column=1, sticky='e', padx=5)

# Rotation mode entry
tk.Label(rotation_frame, text="Rotation Mode (D=Default, L=Left, R=Right):").grid(row=4, column=0, sticky='w', padx=5)
rotation_mode_entry = tk.Entry(rotation_frame, width=5)
rotation_mode_entry.insert(0, "D")  # Default to D
rotation_mode_entry.grid(row=4, column=1, sticky='w', padx=5)

# Add validation to only allow 1 character
def validate_rotation_mode_input(new_text):
    if len(new_text) > 1:
        return False
    return True

rotation_mode_entry.config(validate="key")
rotation_mode_entry.config(validatecommand=(rotation_mode_entry.register(validate_rotation_mode_input), '%P'))

# Add this function to save output to text file
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
            with open(file_path, 'w') as f:
                f.write(content)
            status_label.config(text=f"Output saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

def clear_output():
    answer = messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the output?")
    if answer:
        output_text.delete('1.0', tk.END)


# --- RUN BUTTONS ---
run_button = tk.Button(scrollable_frame, text="Run qpAdm", command=run_qpadm, bg="lightblue")
run_button.grid(row=7, column=0, columnspan=2, pady=10, sticky='we')

edit_run_button = tk.Button(scrollable_frame, text="Edit and Run R Code", command=edit_and_run_r_code, bg="lightyellow")
edit_run_button.grid(row=7, column=2, pady=10, sticky='we')

rotation_run_button = tk.Button(
    scrollable_frame, 
    text="Run Rotation Analysis", 
    command=run_rotation, 
    bg="#90EE90"
)
rotation_run_button.grid(row=8, column=0, columnspan=3, pady=10, sticky='we')

# Create a frame for the buttons
button_frame = tk.Frame(scrollable_frame)
button_frame.grid(row=11, column=2, sticky='e', padx=10, pady=(0, 10))  # Modified row from 11 to 10

# Clear button
clear_button = tk.Button(button_frame, text="Clear", command=clear_output, bg="lightgray", width=10, height=1)
clear_button.pack(side=tk.LEFT, padx=5)


#Button
save_output_button = tk.Button(button_frame, text="💾 Save", command=save_output_to_file, bg="lightgray", width=10, height=1)
save_output_button.pack(side=tk.LEFT)

# --- OUTPUT CONSOLE ---
output_text = scrolledtext.ScrolledText(scrollable_frame, width=150, height=30, undo=True)
output_text.grid(row=10, column=0, columnspan=3, padx=10, pady=5, sticky='nsew')

scrollable_frame.grid_rowconfigure(7, weight=1)

# Status label
status_label = tk.Label(scrollable_frame, text="Ready.", anchor='w')
status_label.grid(row=11, column=0, columnspan=2, sticky='w', padx=10, pady=(0, 10))  # Modified line

# Column configuration
scrollable_frame.grid_columnconfigure(1, weight=1)
scrollable_frame.grid_columnconfigure(2, weight=0)

# --- Repeating Vertical Text Label on the Right ---
word = 'pepsimanfire'
repeat_count = 6  # You can increase this to make it go further down
vertical_text = '\n'.join(list(word) * repeat_count)

vertical_label = tk.Label(scrollable_frame, text=vertical_text, font=("Helvetica", 12, "bold"), fg="gray")
vertical_label.grid(row=0, column=3, rowspan=999, sticky='ns', padx=(60, 5), pady=10)

# Call this function after creating the output_text widget
setup_output_search()

# --- Output Console Bindings ---
output_text.bind('<Control-z>', lambda e: output_text.edit_undo())

root.bind('<Control-z>', lambda e: undo_population_addition())
root.bind('<Control-y>', lambda e: redo_population_addition())
root.bind('<Control-Z>', lambda e: undo_population_addition())
root.bind('<Control-Y>', lambda e: redo_population_addition())

root.mainloop()
