🔬 MD Simulation Automation Tool | 分子动力学模拟自动执行工具
这是一个基于 PyQt6 + GROMACS + bash 的全自动化 MD 脚本，用于批量构建、运行、分析并汇总多组蛋白/小分子模拟体系。

This is an automated MD pipeline based on PyQt6 + GROMACS + bash for batch simulation, post-analysis, and data summary across multiple protein or ligand systems.

📦 功能 | Features
✅ 图形界面操作（文件夹选择 + 步骤选择）
✅ 支持 GROMACS 全流程：构建体系 → 能量最小化 → NVT/NPT 平衡 → 生产模拟
✅ 自动后处理：RMSD、RMSF、轨迹中心化、结构导出
✅ 自动提取所有 .xvg 分析结果并汇总为 .csv 文件
✅ 可处理多个子文件夹，每个子文件夹一个模拟体系

🚀 使用方法 | How to Use
1. 安装依赖 | Install Dependencies
确保你使用的是 Linux / WSL2 环境，并已正确安装以下软件：

Python 3.9+

GROMACS 2021+

GPU 加速驱动（可选）

安装依赖包：

bash
pip install pyqt6 pandas numpy
2. 启动程序 | Run the GUI

bash
python run_all_md.py

你将看到一个图形界面：

🔘 选择主文件夹（包含多个模拟子目录，每个目录内含 complex.pdb）

✅ 勾选执行内容（构建 + 分析 + 汇总）

🟢 点击【Confirm and Run】开始批量模拟

3. 目录结构要求 | Directory Structure
cpp

project_folder/
│
├── system1/
│   └── complex.pdb
│
├── system2/
│   └── complex.pdb
│
└── mdps/         ← 可放入 ions.mdp, em.mdp 等参数文件
    ├── ions.mdp
    ├── em.mdp
    ├── nvt.mdp
    ├── npt.mdp
    └── md.mdp

你可以将 .mdp 文件放在任意统一位置，脚本会自动引用该目录下的参数。

4. 生成文件说明 | Output Files
每个子文件夹内将生成：

run_md.sh：自动生成的 bash 脚本

md.xtc, md.tpr, md.gro：模拟轨迹与结构

rmsd.xvg, rmsf.xvg, potential.xvg 等分析文件

*.csv：自动汇总生成的跨组比较表格

📊 汇总功能 | Summary CSV Generator
脚本会自动扫描所有子目录中的 .xvg 文件，并统一输出为 .csv 文件，用于可视化或批量比较：

python-repl

rmsd.csv
rmsf.csv
potential.csv
...

🛠 常见问题 | FAQ
Q1: 路径不存在或找不到 .mdp 文件？
A: 请确保 .mdp 文件路径正确，Python 中使用的是纯字符串格式 {mdps_dir}/xxx.mdp，不要包含 $ 符号。

Q2: 程序没反应？
A: 检查 Python 是否装好 pyqt6，命令行运行 python run_all_md.py 看是否弹出窗口。

Q3: 有 GPU 吗？
A: 脚本使用 -nb gpu -pme gpu，支持 GROMACS GPU 加速。建议安装 GROMACS 2021+ 并验证 gmx mdrun 支持 GPU。

👨‍💻 作者 | Author
Terry Wang
Terrywangtianyu@gmail.com
Date: 2025-06
