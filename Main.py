import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import mysql.connector
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from sqlalchemy import create_engine
import itertools
from collections import defaultdict

config = {
    'user': '',
    'password': '',
    'host': '',
    'database': '',
    'ssl_ca': '',
    'ssl_cert': '',
    'ssl_key': ''
}

def get_sqlalchemy_engine():
    return create_engine(
        f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}/{config['database']}",
        connect_args={'ssl_ca': config['ssl_ca'], 'ssl_cert': config['ssl_cert'], 'ssl_key': config['ssl_key']}
    )

def connect_to_db():
    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            print("Successfully connected to the database")
            return connection
    except mysql.connector.Error as err:
        print("Error:", err)
    return None

def reconnect_if_needed(connection):
    try:
        if not connection.is_connected():
            print("Reconnecting to the database...")
            connection.reconnect(attempts=3, delay=2)
    except mysql.connector.Error as err:
        print(f"Error reconnecting: {err}")
        return None

def hamming_distance(fingerprint_a, fingerprint_b):
    fingerprint_a = np.frombuffer(fingerprint_a, dtype=np.uint8)
    fingerprint_b = np.frombuffer(fingerprint_b, dtype=np.uint8)
    min_len = min(len(fingerprint_a), len(fingerprint_b))
    fingerprint_a, fingerprint_b = fingerprint_a[:min_len], fingerprint_b[:min_len]
    return np.sum(np.unpackbits(fingerprint_a) != np.unpackbits(fingerprint_b))

def compute_mean_hamming_distances(selected_data):
    distances = []
    for i in range(len(selected_data)):
        for j in range(i + 1, len(selected_data)):
            dist = hamming_distance(selected_data.iloc[i]['Fingerprint'], selected_data.iloc[j]['Fingerprint'])
            dist_percent = dist / (len(selected_data.iloc[i]['Fingerprint']) * 8)
            distances.append(dist_percent)
    return distances

class MeasurementSearcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Measurement Searcher")
        self.geometry("1600x1100")
        self.connection = connect_to_db()
        self.create_widgets()
        self.last_clicked_index = {}
        self.load_board_ids_for_all()

    def create_filter_group(self, parent, label_prefix):
        group = {}
        fields = [
            ('Board ID', 'board_listbox'),
            ('Region Start (Hex)', 'region_start_entry'),
            ('Region End (Hex)', 'region_end_entry'),
            ('Min Temp (°C)', 'temp_min_entry'),
            ('Max Temp (°C)', 'temp_max_entry'),
            ('Timestamp: (YYYY-MM-DD)', 'timestamp_entry')
        ]

        for text, key in fields:
            tk.Label(parent, text=f"{text}").pack(anchor='w')
            if 'listbox' in key:
                frame = tk.Frame(parent)
                frame.pack()
                widget = tk.Listbox(frame, selectmode=tk.MULTIPLE, width=20, height=5, exportselection=False)

                scrollbar = tk.Scrollbar(frame, orient='vertical', command=widget.yview)
                widget.config(yscrollcommand=scrollbar.set)
                widget.pack(side='left')
                scrollbar.pack(side='right', fill='y')

                widget.bind("<Button-1>", lambda e, lb=widget: self.on_click(lb, e))
                widget.bind("<Shift-Button-1>", lambda e, lb=widget: self.on_shift_click(lb, e))
                widget.bind("<Double-Button-1>", lambda e, lb=widget: self.toggle_all_selection(lb))

            else:
                widget = tk.Entry(parent, width=22)
            widget.pack(pady=(0, 5))
            group[key] = widget

        #result_list
        tk.Label(parent, text=f"Results").pack(anchor='w', pady=(10, 0))
        result_frame = tk.Frame(parent)
        result_frame.pack()
        result_list = tk.Listbox(result_frame, width=75, height=10, selectmode=tk.MULTIPLE, exportselection=False)

        scrollbar = tk.Scrollbar(result_frame, orient='vertical', command=result_list.yview)
        result_list.config(yscrollcommand=scrollbar.set)
        result_list.pack(side='left')
        scrollbar.pack(side='right', fill='y')

        result_list.bind("<Button-1>", lambda e, lb=result_list: self.on_click(lb, e))
        result_list.bind("<Shift-Button-1>", lambda e, lb=result_list: self.on_shift_click(lb, e))
        result_list.bind("<Double-Button-1>", lambda e, lb=result_list: self.toggle_all_selection(lb))

        group['result_list'] = result_list
        return group

    def create_widgets(self):
        self.filters = {}

        # Top Frame for Filters
        top_frame = tk.Frame(self)
        top_frame.pack(pady=10, padx=10, fill='x')

        for i, label in enumerate(['A', 'B', 'C']):
            group_frame = tk.LabelFrame(top_frame, text=f"List {label}", padx=10, pady=10)
            group_frame.pack(side='left', padx=10, fill='y', expand=True)
            self.filters[label] = self.create_filter_group(group_frame, f"List {label}")

            load_btn = tk.Button(group_frame, text="Load Selection",
                                 command=lambda l=label: self.load_selection(l))
            load_btn.pack(pady=5)

        # Middle Frame for Graph + Buttons
        middle_frame = tk.Frame(self)
        middle_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Left Buttons
        left_buttons = tk.Frame(middle_frame, width=100)
        left_buttons.pack(side='left', padx=10, fill='y')
        tk.Button(left_buttons, text="Comparison", width=15, command=self.calculate_hd_per_board).pack(pady=5)
        tk.Button(left_buttons, text="Bit Stability", width=15, command=self.calculate_bit_stability).pack(pady=5)

        # Graph Placeholder
        graph_frame = tk.Frame(middle_frame, bg="#ffffff", relief='ridge')
        graph_frame.pack(side='left', expand=True, fill='both', padx=10)
        self.graph_placeholder = tk.Frame(graph_frame, bg="#ffffff", width=800, height=500, relief='groove', bd=2)
        self.graph_placeholder.pack_propagate(False)
        self.graph_placeholder.pack(fill='both', expand=True)

        # Right Buttons
        right_buttons = tk.Frame(middle_frame, width=100)
        right_buttons.pack(side='right', padx=10, fill='y')
        tk.Button(right_buttons, text="Mean HD", width=15, command=self.calculate_mean_hd).pack(pady=5)
        tk.Button(right_buttons, text="Uniqueness", width=15, command=self.calculate_uniqueness).pack(pady=5)

    def toggle_all_selection(self, listbox):
        if listbox.size() == 0:
            return
        cur_selection = listbox.curselection()
        if len(cur_selection) == listbox.size():
            listbox.selection_clear(0, tk.END)
        else:
            listbox.selection_set(0, tk.END)

    def on_click(self, listbox, event):
        listbox.last_clicked_index = listbox.nearest(event.y)

    def on_shift_click(self, listbox, event):
        if not hasattr(listbox, 'last_clicked_index') or listbox.last_clicked_index is None:
            return

        clicked_index = listbox.nearest(event.y)
        start = min(listbox.last_clicked_index, clicked_index)
        end = max(listbox.last_clicked_index, clicked_index)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(start, end)

    def load_selection(self, label):
        f = self.filters[label]
        board_ids = [f['board_listbox'].get(i) for i in f['board_listbox'].curselection()]
        region_start = f['region_start_entry'].get()
        region_end = f['region_end_entry'].get()
        timestamp = f['timestamp_entry'].get()
        temp_min = f['temp_min_entry'].get()
        temp_max = f['temp_max_entry'].get()

        f['result_list'].delete(0, tk.END)

        if not board_ids:
            messagebox.showerror("Input Error", f"List {label}: At least one Board ID must be selected.")
            return

        query = """
        SELECT b.BoardId, b.BoardSpecifier, r.PufStart, r.PufEnd, r.Temperature, r.Timestamp, r.Fingerprint
        FROM Boards b
        JOIN Readings r ON b.BoardId = r.BoardId
        WHERE
        """

        conditions = [f"b.BoardId IN ({', '.join(f'{b}' for b in board_ids)})"]

        try:
            if region_start:
                region_start_dec = int(region_start, 16)
                conditions.append(f"r.PufStart <= {region_start_dec}")
            if region_end:
                region_end_dec = int(region_end, 16)
                conditions.append(f"r.PufEnd >= {region_end_dec}")
        except ValueError:
            messagebox.showerror("Input Error", f"List {label}: Invalid hex format for region addresses.")
            return

        if timestamp:
            conditions.append(f"DATE(r.Timestamp) = '{timestamp}'")
        if temp_min:
            conditions.append(f"r.Temperature >= {temp_min}")
        if temp_max:
            conditions.append(f"r.Temperature <= {temp_max}")

        query += " AND ".join(conditions)

        engine = get_sqlalchemy_engine()
        df = pd.read_sql(query, engine)

        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d')
            for _, row in df.iterrows():
                f['result_list'].insert(tk.END, f"BId: {row['BoardId']}, BS: {row['BoardSpecifier']}, "
                                                f"Temp: {row['Temperature']}°C, PStart: {hex(row['PufStart'])}, "
                                                f"PEnd: {hex(row['PufEnd'])}, Time: {row['Timestamp']}")

            setattr(self, f"loaded_df_{label.lower()}", df)
        else:
            f['result_list'].insert(tk.END, "No results found.")
            setattr(self, f"loaded_df_{label.lower()}", None)

    def load_board_ids_for_all(self):
        if self.connection:
            query = "SELECT DISTINCT BoardId FROM Boards"
            df = pd.read_sql(query, self.connection)
            for group in self.filters.values():
                group['board_listbox'].delete(0, tk.END)
                for board_id in df["BoardId"]:
                    group['board_listbox'].insert(tk.END, board_id)

    def calculate_mean_hd(self):
        datasets = {}
        styles = {'a': 'dashed', 'b': 'solid', 'c': 'dotted'}

        for label in ['a', 'b', 'c']:
            df = getattr(self, f"loaded_df_{label}", None)
            if df is not None and not df.empty:
                selected = self.filters[label.upper()]['result_list'].curselection()
                if selected:
                    selected_data = df.iloc[list(selected)]

                    # Filter out any entries without a valid Fingerprint
                    selected_data = selected_data[selected_data['Fingerprint'].notnull()]

                    if len(selected_data) > 1:
                        distances = compute_mean_hamming_distances(selected_data)
                        datasets[label] = distances

        if not datasets:
            messagebox.showerror("Selection Error", f"No valid data selected from any List.")
            return

        for widget in self.graph_placeholder.winfo_children():
            widget.destroy()

        # Plot the graph
        fig, ax = plt.subplots()

        colors = {'a': 'black', 'b': 'black', 'c': 'black'}

        for label, distances in datasets.items():
            sns.kdeplot(distances,
                        linestyle=styles[label],
                        color=colors[label],
                        label=f"List {label.upper()}",
                        fill=False,
                        clip=(0, 1))

        ax.set_xlabel("Fractional Hamming Distance", fontsize=12)
        ax.set_ylabel("Probability Density", fontsize=12)
        ax.legend(fontsize=10.5)
        ax.set_aspect(1.0 / ax.get_data_ratio(), adjustable='box')
        plt.savefig('Mean_HD_Combined_Plot.pdf', format='pdf', bbox_inches='tight')
        plt.show()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_placeholder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def calculate_uniqueness(self):
        datasets = {}
        styles = {'a': 'dashed', 'b': 'solid', 'c': 'dotted'}

        for label in ['a', 'b', 'c']:
            df = getattr(self, f"loaded_df_{label}", None)
            if df is not None and not df.empty:
                selected = self.filters[label.upper()]['result_list'].curselection()
                if selected:
                    selected_data = df.iloc[list(selected)]
                    selected_data = selected_data[selected_data['Fingerprint'].notnull()]
                    if len(selected_data) > 1:

                        # Compute uniqueness
                        uniq_vals = []
                        for i in range(len(selected_data)):
                            fp1 = np.unpackbits(np.frombuffer(selected_data.iloc[i]['Fingerprint'], dtype=np.uint8))
                            for j in range(i + 1, len(selected_data)):
                                fp2 = np.unpackbits(np.frombuffer(selected_data.iloc[j]['Fingerprint'], dtype=np.uint8))
                                min_len = min(len(fp1), len(fp2))
                                fp1_trim, fp2_trim = fp1[:min_len], fp2[:min_len]
                                uniqueness = np.sum(fp1_trim != fp2_trim) / min_len
                                uniq_vals.append(uniqueness)
                        datasets[label] = uniq_vals

        if not datasets:
            messagebox.showerror("Selection Error", "No valid data selected from any box.")
            return

        for widget in self.graph_placeholder.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots()

        colors = {'a': 'black', 'b': 'black', 'c': 'black'}

        for label, values in datasets.items():
            sns.kdeplot(values,
                        linestyle=styles[label],
                        color=colors[label],
                        label=f"List {label.upper()} Uniqueness",
                        fill=False,
                        clip=(0, 1))

        ax.set_xlabel("Fractional Hamming Distance", fontsize=12)
        ax.set_ylabel("Probability Density", fontsize=12)
        ax.legend(fontsize=10.5)
        ax.set_aspect(1.0 / ax.get_data_ratio(), adjustable='box')
        plt.savefig('Uniqueness_Combined_Plot.pdf', format='pdf', bbox_inches='tight')
        plt.show()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_placeholder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def calculate_hd_per_board(self):
        datasets = {}

        # Define a colormap for more unique colors
        color_map = plt.colormaps.get_cmap('tab20')
        colors = [color_map(i/20) for i in range(20)]
        color_cycle = itertools.cycle(color_map.colors)

        boardid_to_color = {}

        for label in ['a', 'b', 'c']:
            df = getattr(self, f"loaded_df_{label}", None)
            if df is not None and not df.empty:
                selected = self.filters[label.upper()]['result_list'].curselection()
                if selected:
                    selected_data = df.iloc[list(selected)]
                    selected_data = selected_data[selected_data['Fingerprint'].notnull()]
                    grouped = selected_data.groupby('BoardId')
                    grouped = selected_data.groupby('BoardId')

                    board_datasets = {}
                    for board_id, group in grouped:
                        if len(group) > 1:
                            board_datasets[(label, board_id)] = compute_mean_hamming_distances(group)
                    datasets[label] = board_datasets

        if not datasets:
            messagebox.showerror("Selection Error", "No valid data selected for HD per Board plot.")
            return

        for widget in self.graph_placeholder.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots()

        line_index = 0
        for label, board_data in datasets.items():
            for board_key, distances in board_data.items():
                color = color_map(line_index / 20)
                ax.plot(
                    distances,
                    label=f"List {label.upper()} - Board {board_key[1]}",
                    color=color,
                    linestyle='-'
                )
                line_index += 1

        ax.set_xlabel("Comparison Index", fontsize=12)
        ax.set_ylabel("Fractional Hamming Distance", fontsize=12)
        ax.legend(fontsize=9)
        plt.tight_layout()
        plt.savefig('HD_Per_Board.pdf', format='pdf', bbox_inches='tight')
        plt.show()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_placeholder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def calculate_bit_stability(self):

        max_samples = 250
        datasets = defaultdict(list)
        styles = {'a': 'x', 'b': '+', 'c': '.'}

        for label in ['a', 'b', 'c']:
            df = getattr(self, f"loaded_df_{label}", None)
            if df is not None and not df.empty:
                selected = self.filters[label.upper()]['result_list'].curselection()
                if selected:
                    selected_data = df.iloc[list(selected)]
                    selected_data = selected_data[selected_data['Fingerprint'].notnull()]

                    if len(selected_data) < 2:
                        continue

                    # Convert fingerprints to bit arrays
                    bit_arrays = [
                        np.unpackbits(np.frombuffer(row['Fingerprint'], dtype=np.uint8))
                        for _, row in selected_data.iterrows()
                    ]

                    #bit_arrays = np.array(bit_arrays)
                    min_len = min(arr.size for arr in bit_arrays)
                    bit_arrays = np.array([arr[:min_len] for arr in bit_arrays])

                    for num_samples in range(1, min(max_samples, len(bit_arrays)) + 1):
                        subset = bit_arrays[:num_samples]
                        stable_bits = np.sum(np.all(subset == subset[0], axis=0))
                        stable_ratio = stable_bits / min_len
                        datasets[label].append(stable_ratio)

        if not datasets:
            messagebox.showerror("Selection Error", "No valid data to compute Bit Stability.")
            return

        for widget in self.graph_placeholder.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots()

        for label, stability_vals in datasets.items():
            ax.plot(range(1, len(stability_vals) + 1), stability_vals, marker=styles[label],
                    linestyle='none', label=f"{label.upper()}", color="black")

        ax.set_xlabel("Samples", fontsize=12)
        ax.set_ylabel("Stable Bits / Total Bits", fontsize=12)
        ax.legend(fontsize=10.5)
        ax.set_ylim(0.65, 1.0)
        ax.set_xlim(0, max(len(v) for v in datasets.values()) + 5)
        plt.tight_layout()
        plt.savefig("Bit_Stability.pdf", format='pdf', bbox_inches="tight")
        plt.show()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_placeholder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    app = MeasurementSearcher()
    app.mainloop()
