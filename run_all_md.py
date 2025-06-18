import os
import subprocess
import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QApplication, QFileDialog, QCheckBox, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QFont

class MDGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MD Simulation Launcher")
        self.setFixedSize(500, 300)
        self.center()

        font = QFont()
        font.setPointSize(14)  # 默认是10或11，改成14表示放大一倍
        self.setFont(font)

        self.layout = QVBoxLayout()

        self.path_label = QLabel("No folder selected")
        self.layout.addWidget(self.path_label)

        self.select_folder_btn = QPushButton("Select Input Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.layout.addWidget(self.select_folder_btn)

        self.simulate_cb = QCheckBox("1. Run Simulation")
        self.simulate_cb.setChecked(True)
        self.layout.addWidget(self.simulate_cb)

        self.analyze_cb = QCheckBox("2. Post Analysis")
        self.analyze_cb.setChecked(True)
        self.layout.addWidget(self.analyze_cb)

        self.summary_cb = QCheckBox("3. Summary Report")
        self.summary_cb.setChecked(True)
        self.layout.addWidget(self.summary_cb)

        self.confirm_btn = QPushButton("Confirm and Run")
        self.confirm_btn.clicked.connect(self.confirm)
        self.layout.addWidget(self.confirm_btn)

        self.setLayout(self.layout)
        self.folder = None
        self.selection_result = None

    def center(self):
        screen = QApplication.primaryScreen().geometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())

    def select_folder(self):
        dialog = QFileDialog()
        folder = dialog.getExistingDirectory(self, "Select Root Directory")
        if folder:
            self.folder = folder
            self.path_label.setText(f"Selected: {folder}")

    def confirm(self):
        if not self.folder:
            QtWidgets.QMessageBox.warning(self, "Error", "No folder selected.")
            return
        self.selection_result = (
            self.simulate_cb.isChecked(),
            self.analyze_cb.isChecked(),
            self.summary_cb.isChecked(),
            self.folder
        )
        self.close()

app = QApplication(sys.argv)
gui = MDGui()
gui.show()
app.exec()

if not gui.selection_result:
    print("No steps or folder selected. Exiting.")
    sys.exit(1)

do_simulation, do_analysis, do_summary, root_dir = gui.selection_result

mdps_dir = root_dir  # Directory containing ions.mdp, em.mdp, etc.

if do_simulation or do_analysis:
    # Traverse all subdirectories
    for subfolder in sorted(os.listdir(root_dir)):
        sub_path = os.path.join(root_dir, subfolder)
        if not os.path.isdir(sub_path):
            continue
        if not os.path.exists(os.path.join(sub_path, "complex.pdb")):
            continue

        print(f"Starting MD for {subfolder}...")

        bash_script = f"""#!/bin/bash
source /usr/local/gromacs/bin/GMXRC
cd "{sub_path}"

# Select force field number 6
gmx pdb2gmx -f complex.pdb -o processed.gro -water tip3p -ignh << EOF
6
EOF

# Define box
gmx editconf -f processed.gro -o box.gro -c -d 1.0 -bt cubic

# Add solvent
gmx solvate -cp box.gro -cs spc216.gro -o solv.gro -p topol.top

# Add ions, select group 13 (SOL)
gmx grompp -f {mdps_dir}/ions.mdp -c solv.gro -p topol.top -o ions.tpr
echo 13 | gmx genion -s ions.tpr -o solv_ions.gro -p topol.top -neutral -conc 0.15

# Energy minimization
gmx grompp -f {mdps_dir}/em.mdp -c solv_ions.gro -p topol.top -o em.tpr
gmx mdrun -v -deffnm em -nb gpu -pin on

# NVT equilibration
gmx grompp -f {mdps_dir}/nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr
gmx mdrun -v -deffnm nvt -nb gpu -pin on

# NPT equilibration
gmx grompp -f {mdps_dir}/npt.mdp -c nvt.gro -p topol.top -o npt.tpr
gmx mdrun -v -deffnm npt -nb gpu -pin on

# Production MD
gmx grompp -f {mdps_dir}/md.mdp -c npt.gro -p topol.top -o md.tpr
gmx mdrun -v -deffnm md -nb gpu -pin on -ntmpi 1 -ntomp 12 -pme gpu

# ================= Post-processing analysis =================

# Export system total energy (Potential)
echo 11 0 | gmx energy -f md.edr -o potential.xvg

    # Trajectory correction: nojump -> fit -> center
echo 1 1 | gmx trjconv -s md.tpr -f md.xtc -o md_nojump.xtc -pbc nojump
echo 1 1 | gmx trjconv -s md.tpr -f md_nojump.xtc -o md_fit.xtc -fit rot+trans
echo 1 1 | gmx trjconv -s md.tpr -f md_fit.xtc -o md_center.xtc -center -pbc mol

    # RMSD calculation
    echo 1 1 | gmx rms -s md.tpr -f md_center.xtc -o rmsd.xvg -tu ns

    # RMSF calculation
echo 1 1 | gmx rmsf -s md.tpr -f md_center.xtc -o rmsf.xvg -res
    # Trajectory visualization
echo 1 1 | gmx trjconv -s md.tpr -f md_center.xtc -o md_vis.pdb -dt 1000
    """

        if do_analysis:
            # keep full script
            script_path = os.path.join(sub_path, "run_md.sh")
            with open(script_path, "w") as f:
                f.write(bash_script)
            subprocess.run(["chmod", "+x", script_path])
            subprocess.run(["bash", script_path])
        elif do_simulation:
            # strip the script at post-analysis part
            split_script = bash_script.split("# ================= Post-processing analysis =================")[0]
            script_path = os.path.join(sub_path, "run_md.sh")
            with open(script_path, "w") as f:
                f.write(split_script)
            subprocess.run(["chmod", "+x", script_path])
            subprocess.run(["bash", script_path])

if do_summary:
    print("Starting summary analysis...")

    import pandas as pd
    import numpy as np
    import glob
    import re
    from collections import defaultdict

    def process_xvg_file(filepath):
        data = []
        with open(filepath, 'r', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                if line.startswith(('#', '@')):
                    continue
                try:
                    values = []
                    for val in line.strip().split():
                        val = val.strip()
                        if val:
                            try:
                                values.append(float(val))
                            except ValueError:
                                print(f"Warning: Unconvertible value '{val}' at line {line_num} in file {filepath}, skipped")
                                continue
                    if values:
                        data.append(values)
                except Exception as e:
                    print(f"Error processing line {line_num} in file {filepath}: {str(e)}, skipped")
                    continue
        if not data:
            print(f"Warning: No valid data extracted from file {filepath}")
            return np.array([])
        max_cols = max(len(row) for row in data) if data else 0
        for i in range(len(data)):
            if len(data[i]) < max_cols:
                data[i] = data[i] + [np.nan] * (max_cols - len(data[i]))
        return np.array(data)

    def summarize_xvg_data(root_folder):
        subfolders = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f))]
        if not subfolders:
            print(f"No subfolders found in {root_folder}")
            return

        print(f"Found subfolders: {subfolders}")

        xvg_file_patterns = set()
        for subfolder in subfolders:
            subfolder_path = os.path.join(root_folder, subfolder)
            xvg_files = glob.glob(os.path.join(subfolder_path, "*.xvg"))
            for xvg_file in xvg_files:
                file_basename = os.path.basename(xvg_file)
                xvg_file_patterns.add(file_basename)

        if not xvg_file_patterns:
            print("No XVG files found")
            return

        print(f"Found XVG file patterns: {xvg_file_patterns}")

        for xvg_pattern in xvg_file_patterns:
            file_data = defaultdict(list)
            max_rows = 0
            x_column = None
            pattern_name = os.path.splitext(xvg_pattern)[0]
            print(f"Processing {pattern_name} files...")

            for subfolder in subfolders:
                subfolder_path = os.path.join(root_folder, subfolder)
                xvg_file_path = os.path.join(subfolder_path, xvg_pattern)

                if os.path.exists(xvg_file_path):
                    print(f"  Processing file: {xvg_file_path}")
                    try:
                        data = process_xvg_file(xvg_file_path)
                        if data.size > 0:
                            if data.shape[1] >= 2:
                                file_data[subfolder] = data[:, 1]
                                if len(data) > max_rows:
                                    max_rows = len(data)
                                    x_column = data[:, 0]
                                print(f"  - Read {len(data)} rows from {subfolder}")
                            else:
                                print(f"  - Warning: Data in {xvg_file_path} has fewer than 2 columns")
                        else:
                            print(f"  - Warning: No valid data extracted from {xvg_file_path}")
                    except Exception as e:
                        print(f"  - Error processing {xvg_file_path}: {str(e)}")
                else:
                    print(f"  File not found: {xvg_file_path}")

            if x_column is not None and max_rows > 0 and file_data:
                try:
                    output_df = pd.DataFrame()
                    output_df['x'] = x_column
                    for subfolder, data in file_data.items():
                        if len(data) < max_rows:
                            padded_data = np.full(max_rows, np.nan)
                            padded_data[:len(data)] = data
                            output_df[subfolder] = padded_data
                        else:
                            output_df[subfolder] = data
                    csv_filename = pattern_name + '.csv'
                    csv_path = os.path.join(root_folder, csv_filename)
                    output_df.to_csv(csv_path, index=False)
                    print(f"CSV file generated: {csv_path}")
                except Exception as e:
                    print(f"Error generating CSV file {pattern_name}.csv: {str(e)}")
            else:
                print(f"Insufficient data to generate CSV for {pattern_name}")

    summarize_xvg_data(root_dir)
    print("Summary analysis completed.")
