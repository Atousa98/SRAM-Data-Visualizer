# Embedded Systems SRAM Data Visualizer & Analyzer

A Python-based graphical user interface (GUI) developed during my time at the Embedded Systems Laboratory to extract, process, and analyze hidden fingerprint data from SRAM components.

## Overview
This tool was built to bridge the gap between hardware readings and data analysis in a fast-paced research environment. It allows researchers to filter measurements from different boards based on regions, temperatures, and timestamps, and directly compute hardware security metrics.

### Key Features
- **Database Integration:** Connects securely to a MySQL database to fetch raw hardware readings.
- **Advanced Metrics:** Computes Fractional Hamming Distance, Uniqueness, and Bit Stability across multiple samples.
- **Data Visualization:** Embedded matplotlib/seaborn plots within the Tkinter UI for live data analysis.

## User Interface & Data Analysis
![SRAM Data Visualizer Interface](https://github.com/Atousa98/SRAM-Data-Visualizer/releases/download/v1.0.0/tool.png)

## Technical Stack
- **Language:** Python
- **GUI Framework:** Tkinter
- **Data & Math:** Pandas, NumPy, SQLAlchemy, Itertools
- **Plotting:** Matplotlib, Seaborn

## Engineering Reflection (Self-Review)
*Note: This repository contains the raw, original codebase developed in the lab to meet immediate research objectives under tight cycles. Looking back with a software engineering mindset, I recognize several areas for future refactoring:*

1. **Architecture:** The current implementation follows a monolithic structure (UI and logic combined). In a production environment, I would decouple this into a clean **MVC (Model-View-Controller)** pattern.
2. **Concurrency (Threading):** Heavy cryptographic/Hamming calculations currently run on the main UI thread, causing temporary interface freezing. Implementing Python's `threading` or `asyncio` for background processing would greatly improve UX.
3. **Security:** SQL query generation uses direct string formatting for dynamic filtering. For a public-facing application, utilizing parameterized queries is essential to eliminate any risk of SQL injection.