# Elite Squad Optimizer: A Prescriptive Analytics Pipeline for Football Scouting
<img width="100%" alt="Dashboard Preview" src="https://github.com/user-attachments/assets/57f6d634-9c04-4536-81c8-3783a69a234f" />

## Introduction
Elite-Squad-Optimizer is a Python-based prescriptive analytics pipeline designed to solve the "Ideal Starting XI" selection problem. By combining real-time performance data with market values, the project utilizes Mathematical Programming (Linear Programming) to maximize team quality under strict financial and tactical constraints.

The pipeline integrates automated ETL processes via Google Colab, high-performance data warehousing in Google BigQuery, and a Mixed-Integer Programming (MIP) solver using the Gurobi Optimizer. The final output is an interactive Streamlit application that allows scouts to adjust tactical formations and performance weights dynamically.

## Features
Advanced ETL & Data Cleansing: Implement automated deduplication and normalization of player stats across disparate API sources and Transfermarkt data.

Position-Specific Scoring: Support custom SQL-based performance logic that weights metrics (Expected Goals, Interceptions, Key Passes) differently based on the player's tactical role.

Mathematical Optimization: Support the "Knapsack Problem" formulation using Gurobi to guarantee a globally optimal solution for any budget range.

Dynamic Formations: Support multiple tactical setups (4-3-3, 4-4-2, 3-5-2) with automated position constraint mapping.

Cloud Infrastructure: Fully deployed on Streamlit Cloud with secure GCP Service Account integration via encrypted TOML secrets.

## Installation
Clone and install from this repository. You can download the project using git:

```Bash
git clone https://github.com/bttisrael/football-scout-optimizer.git
cd football-scout-optimizer
```
Install the required packages using pip:
```Bash
pip install -r requirements.txt
```
## Usage & Sample Code
The main execution is performed via the Streamlit interface, while the optimization engine is powered by Gurobi. Below is a simplified snippet demonstrating the Constrained Optimization formulation implemented in the pipeline:

```Python
import gurobipy as gp
from gurobipy import GRB

# Initialize Model
m = gp.Model("SquadOptimization")

# Decision Variables: x[i] = 1 if player i is selected, else 0
x = m.addVars(df.index, vtype=GRB.BINARY)

# Objective: Maximize total performance score based on position weights
m.setObjective(gp.quicksum(df.performance_score[i] * x[i] for i in df.index), GRB.MAXIMIZE)

# Constraint 1: Total market value must be within user-defined budget
m.addConstr(gp.quicksum(df.market_value_mio[i] * x[i] for i in df.index) <= budget)

# Constraint 2: Formation requirement (e.g., exactly 1 Goalkeeper)
m.addConstr(gp.quicksum(x[i] for i in df.index if df.api_pos[i] == 'Goalkeeper') == 1)

# Solve
m.optimize()
```
## Experiments and Diagnostics
To reproduce the data engineering process and optimization results, refer to the football_optimizer.ipynb notebook. The evaluation yielded the following insights:

Tactical Efficiency: The optimization engine successfully handles datasets of 1,000+ players in milliseconds, providing instant feedback for budget variations.

Position Weighting Impact: The diagnostic analysis shows that shifting "Defense Focus" multipliers from 1.0 to 1.5 dynamically replaces high-scoring offensive full-backs with statistically superior defensive stoppers, validating the sensitivity of the prescriptive model.

## Reference
[1] Bertsimas, D., & Freund, R. (2004). Data, Models, and Decisions: The Fundamentals of Management Science.

[2] Gurobi Optimization, LLC. (2024). Gurobi Optimizer Reference Manual.
