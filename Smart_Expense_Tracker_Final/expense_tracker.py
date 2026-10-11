import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import calendar
import csv
from datetime import date, datetime

# ---------------- DATABASE ----------------
conn = sqlite3.connect("expenses.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL
)
""")
conn.commit()

# ---------------- DATE PICKER ----------------
class CalendarPopup:
    def __init__(self, parent, entry):
        self.entry = entry
        self.win = tk.Toplevel(parent)
        self.win.title("Select Date")
        self.win.resizable(False, False)
        today = date.today()
        self.year, self.month = today.year, today.month
        self.draw()

    def draw(self):
        for w in self.win.winfo_children():
            w.destroy()

        head = tk.Frame(self.win)
        head.pack(pady=8)

        tk.Button(head, text="<", width=3,
                  command=self.previous_month).pack(side="left", padx=2)

        month_choice = ttk.Combobox(
            head, width=11, state="readonly",
            values=[calendar.month_name[m] for m in range(1, 13)]
        )
        month_choice.set(calendar.month_name[self.month])
        month_choice.pack(side="left", padx=2)

        year_choice = ttk.Combobox(
            head, width=7, state="readonly",
            values=list(range(date.today().year - 10, date.today().year + 11))
        )
        year_choice.set(self.year)
        year_choice.pack(side="left", padx=2)

        def change_month_year(event=None):
            self.month = month_choice.current() + 1
            self.year = int(year_choice.get())
            self.draw()

        month_choice.bind("<<ComboboxSelected>>", change_month_year)
        year_choice.bind("<<ComboboxSelected>>", change_month_year)

        tk.Button(head, text=">", width=3,
                  command=self.next_month).pack(side="left", padx=2)

        frame = tk.Frame(self.win)
        frame.pack(padx=8, pady=5)

        for col, name in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
            tk.Label(frame, text=name, width=4,
                     font=("Arial", 9, "bold")).grid(row=0, column=col)

        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), 1):
            for col, day in enumerate(week):
                if day:
                    tk.Button(frame, text=str(day), width=4,
                              command=lambda d=day: self.select_date(d)).grid(
                                  row=row, column=col, padx=1, pady=1)

    def previous_month(self):
        self.month -= 1
        if self.month == 0:
            self.month, self.year = 12, self.year - 1
        self.draw()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month, self.year = 1, self.year + 1
        self.draw()

    def select_date(self, day):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, f"{day:02d}-{self.month:02d}-{self.year}")
        self.win.destroy()

# ---------------- APP HELPERS ----------------
def parse_date(text):
    try:
        return datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        return None

def description_focus(event):
    if description_entry.get() == "Example: Lunch, Bus ticket, Shopping":
        description_entry.delete(0, tk.END)
        description_entry.config(fg=theme["fg"])

def description_leave(event):
    if not description_entry.get().strip():
        description_entry.insert(0, "Example: Lunch, Bus ticket, Shopping")
        description_entry.config(fg=theme["muted"])

# ---------------- CRUD ----------------
def add_or_update():
    d = date_entry.get()
    amount_text = amount_entry.get().strip()
    category = category_combo.get()
    desc = description_entry.get().strip()

    if not parse_date(d):
        messagebox.showerror("Invalid Date", "Please select a valid date.")
        return
    if not amount_text:
        messagebox.showwarning("Missing Amount", "Please enter the amount.")
        return
    if not category:
        messagebox.showwarning("Missing Category", "Please select a category.")
        return
    if not desc or desc == "Example: Lunch, Bus ticket, Shopping":
        messagebox.showwarning("Missing Description", "Please enter a description.")
        return

    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Amount", "Enter a valid positive number.")
        return

    global editing_id
    if editing_id is None:
        cursor.execute(
            "INSERT INTO expenses(date, amount, category, description) VALUES(?,?,?,?)",
            (d, amount, category, desc)
        )
        msg = "Expense added successfully."
    else:
        cursor.execute(
            "UPDATE expenses SET date=?, amount=?, category=?, description=? WHERE id=?",
            (d, amount, category, desc, editing_id)
        )
        msg = "Expense updated successfully."

    conn.commit()
    clear_form()
    refresh()
    messagebox.showinfo("Success", msg)

def edit_expense():
    selected = expense_table.selection()
    if not selected:
        messagebox.showwarning("Select Expense", "Please select an expense to edit.")
        return

    eid = selected[0]
    cursor.execute(
        "SELECT date, amount, category, description FROM expenses WHERE id=?",
        (eid,)
    )
    row = cursor.fetchone()

    if row:
        global editing_id
        editing_id = eid
        date_entry.delete(0, tk.END)
        date_entry.insert(0, row[0])
        amount_entry.delete(0, tk.END)
        amount_entry.insert(0, str(row[1]))
        category_combo.set(row[2])
        description_entry.delete(0, tk.END)
        description_entry.insert(0, row[3])
        description_entry.config(fg=theme["fg"])
        save_button.config(text="UPDATE EXPENSE")

def delete_expense():
    selected = expense_table.selection()
    if not selected:
        messagebox.showwarning("Select Expense", "Please select an expense to delete.")
        return

    if messagebox.askyesno("Confirm Delete", "Delete selected expense?"):
        cursor.execute("DELETE FROM expenses WHERE id=?", (selected[0],))
        conn.commit()
        refresh()

def clear_form():
    global editing_id
    editing_id = None
    amount_entry.delete(0, tk.END)
    category_combo.set("")
    description_entry.delete(0, tk.END)
    description_entry.insert(0, "Example: Lunch, Bus ticket, Shopping")
    description_entry.config(fg=theme["muted"])
    save_button.config(text="ADD EXPENSE")

# ---------------- SEARCH / FILTER ----------------
def clear_filter():
    search_entry.delete(0, tk.END)
    month_combo.set("All Months")
    refresh()

def refresh():
    for item in expense_table.get_children():
        expense_table.delete(item)

    search = search_entry.get().strip().lower()
    selected_month = month_combo.get()
    total_visible = 0

    cursor.execute(
        "SELECT id,date,category,description,amount FROM expenses ORDER BY id DESC"
    )

    for eid, d, category, desc, amount in cursor.fetchall():
        text = f"{d} {category} {desc}".lower()

        if search and search not in text:
            continue

        if selected_month != "All Months":
            parsed = parse_date(d)
            if not parsed:
                continue
            selected_parts = selected_month.rsplit(" ", 1)
            if len(selected_parts) == 2:
                selected_month_name, selected_year = selected_parts
                if (calendar.month_name[parsed.month] != selected_month_name
                        or str(parsed.year) != selected_year):
                    continue

        expense_table.insert(
            "", "end", iid=str(eid),
            values=(d, category, desc, f"₹{amount:.2f}")
        )
        total_visible += amount

    update_dashboard()
    update_category_summary()
    update_chart()

# ---------------- DASHBOARD / BUDGET ----------------
def update_dashboard():
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM expenses")
    overall = cursor.fetchone()[0]

    today_text = date.today().strftime("%d-%m-%Y")
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date=?", (today_text,))
    today_total = cursor.fetchone()[0]

    month_text = date.today().strftime("%m-%Y")
    cursor.execute("SELECT date,amount FROM expenses")
    month_total = 0
    for d, amount in cursor.fetchall():
        p = parse_date(d)
        if p and p.strftime("%m-%Y") == month_text:
            month_total += amount

    try:
        budget = float(budget_entry.get())
    except ValueError:
        budget = 0

    remaining = budget - month_total
    total_label.config(text=f"Total: ₹{overall:.2f}")
    today_label.config(text=f"Today: ₹{today_total:.2f}")
    month_label.config(text=f"This Month: ₹{month_total:.2f}")
    budget_label.config(text=f"Budget Left: ₹{remaining:.2f}")

    if budget > 0 and month_total >= budget:
        budget_label.config(fg="#c62828")
        budget_status.config(text="⚠ Budget limit reached!", fg="#c62828")
    else:
        budget_label.config(fg=theme["fg"])
        budget_status.config(text="Budget is under control", fg="#2e7d32")

def set_budget():
    try:
        budget = float(budget_entry.get())
        if budget < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Budget", "Enter a valid budget amount.")
        return
    update_dashboard()
    messagebox.showinfo("Budget Saved", f"Monthly budget: ₹{budget:.2f}")

# ---------------- CATEGORY SUMMARY ----------------
def get_category_totals():
    totals = {}
    cursor.execute("SELECT category, amount FROM expenses")
    for category, amount in cursor.fetchall():
        totals[category] = totals.get(category, 0) + amount
    return totals

def update_category_summary():
    for item in summary_tree.get_children():
        summary_tree.delete(item)

    totals = get_category_totals()
    for category, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        summary_tree.insert("", "end", values=(category, f"₹{amount:.2f}"))

# ---------------- SIMPLE BAR CHART ----------------
def update_chart():
    chart.delete("all")
    totals = get_category_totals()

    if not totals:
        chart.create_text(280, 130, text="No expense data yet",
                          font=("Arial", 12))
        return

    items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    max_value = max(v for _, v in items)
    max_bars = items[:6]

    bar_width = 55
    gap = 25
    start_x = 35
    base_y = 235
    max_height = 170

    for i, (category, value) in enumerate(max_bars):
        x1 = start_x + i * (bar_width + gap)
        x2 = x1 + bar_width
        height = (value / max_value) * max_height if max_value else 0
        y1 = base_y - height

        chart.create_rectangle(x1, y1, x2, base_y, fill=theme["accent"], outline="")
        chart.create_text((x1+x2)//2, base_y+15, text=category, font=("Arial", 8))
        chart.create_text((x1+x2)//2, y1-10, text=f"₹{value:.0f}", font=("Arial", 8, "bold"))

# ---------------- CSV EXPORT ----------------
def export_csv():
    rows = [expense_table.item(i)["values"] for i in expense_table.get_children()]
    if not rows:
        messagebox.showwarning("No Data", "There are no visible expenses to export.")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )
    if not path:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Category", "Description", "Amount"])
        writer.writerows(rows)

    messagebox.showinfo("Export Complete", "Expenses exported to CSV.")

# ---------------- DARK MODE ----------------
theme = {
    "bg": "#f4f6f8",
    "fg": "#222222",
    "muted": "#777777",
    "entry": "#ffffff",
    "accent": "#4a90e2"
}
dark_mode = False

def apply_theme():
    bg = theme["bg"]
    fg = theme["fg"]

    root.configure(bg=bg)

    for widget in root.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for frame in [form, buttons, filter_frame, dashboard, table_frame, chart_frame, summary_frame]:
        try:
            frame.configure(bg=bg)
        except tk.TclError:
            pass

    for widget in form.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for widget in buttons.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for widget in filter_frame.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for widget in dashboard.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for widget in summary_frame.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            pass

    for entry in [date_entry, amount_entry, description_entry, search_entry, budget_entry]:
        entry.configure(bg=theme["entry"], fg=fg, insertbackground=fg)

    description_entry.configure(
        fg=theme["muted"] if description_entry.get() == "Example: Lunch, Bus ticket, Shopping" else fg
    )

    toggle_button.configure(text="☀ Light Mode" if dark_mode else "🌙 Dark Mode")
    chart.configure(bg=theme["entry"])

def toggle_dark_mode():
    global dark_mode, theme
    dark_mode = not dark_mode

    if dark_mode:
        theme = {
            "bg": "#1e1e1e",
            "fg": "#f2f2f2",
            "muted": "#aaaaaa",
            "entry": "#2d2d2d",
            "accent": "#64b5f6"
        }
    else:
        theme = {
            "bg": "#f4f6f8",
            "fg": "#222222",
            "muted": "#777777",
            "entry": "#ffffff",
            "accent": "#4a90e2"
        }

    apply_theme()
    update_chart()

def close_app():
    conn.close()
    root.destroy()

# ---------------- MAIN WINDOW ----------------
root = tk.Tk()
root.title("Smart Expense Tracker")
root.geometry("1100x820")
root.resizable(False, False)

editing_id = None

title_label = tk.Label(
    root, text="SMART EXPENSE TRACKER",
    font=("Arial", 24, "bold")
)
title_label.pack(pady=10)

dashboard = tk.Frame(root)
dashboard.pack(pady=4)

total_label = tk.Label(dashboard, text="Total: ₹0.00",
                       font=("Arial", 11, "bold"), width=20)
total_label.grid(row=0, column=0, padx=4)

today_label = tk.Label(dashboard, text="Today: ₹0.00",
                       font=("Arial", 11, "bold"), width=20)
today_label.grid(row=0, column=1, padx=4)

month_label = tk.Label(dashboard, text="This Month: ₹0.00",
                       font=("Arial", 11, "bold"), width=20)
month_label.grid(row=0, column=2, padx=4)

budget_label = tk.Label(dashboard, text="Budget Left: ₹0.00",
                        font=("Arial", 11, "bold"), width=20)
budget_label.grid(row=0, column=3, padx=4)

form = tk.Frame(root)
form.pack(pady=5)

tk.Label(form, text="Date:", font=("Arial", 11)).grid(row=0,column=0,padx=8,pady=4,sticky="w")
date_entry = tk.Entry(form, width=18)
date_entry.grid(row=0,column=1,padx=5,pady=4)
date_entry.insert(0, date.today().strftime("%d-%m-%Y"))
tk.Button(form, text="📅 Select Date",
          command=lambda: CalendarPopup(root, date_entry),
          width=14).grid(row=0,column=2,padx=5,pady=4)

tk.Label(form, text="Amount:", font=("Arial", 11)).grid(row=1,column=0,padx=8,pady=4,sticky="w")
amount_entry = tk.Entry(form, width=38)
amount_entry.grid(row=1,column=1,columnspan=2,padx=5,pady=4)

tk.Label(form, text="Category:", font=("Arial", 11)).grid(row=2,column=0,padx=8,pady=4,sticky="w")
category_combo = ttk.Combobox(
    form, width=35, state="readonly",
    values=["Food","Travel","Shopping","Education","Bills","Health","Entertainment","Other"]
)
category_combo.grid(row=2,column=1,columnspan=2,padx=5,pady=4)

tk.Label(form, text="Description:", font=("Arial", 11)).grid(row=3,column=0,padx=8,pady=4,sticky="w")
description_entry = tk.Entry(form, width=38, fg="gray")
description_entry.grid(row=3,column=1,columnspan=2,padx=5,pady=4)
description_entry.insert(0, "Example: Lunch, Bus ticket, Shopping")
description_entry.bind("<FocusIn>", description_focus)
description_entry.bind("<FocusOut>", description_leave)

tk.Label(form, text="Monthly Budget:", font=("Arial", 11)).grid(row=4,column=0,padx=8,pady=4,sticky="w")
budget_entry = tk.Entry(form, width=18)
budget_entry.grid(row=4,column=1,padx=5,pady=4,sticky="w")
tk.Button(form, text="SET BUDGET", command=set_budget, width=14).grid(row=4,column=2,padx=5,pady=4)

budget_status = tk.Label(root, text="Budget is under control", font=("Arial", 10, "bold"))
budget_status.pack()

buttons = tk.Frame(root)
buttons.pack(pady=6)

save_button = tk.Button(buttons, text="ADD EXPENSE", command=add_or_update, width=15)
save_button.pack(side="left", padx=4)
tk.Button(buttons, text="EDIT SELECTED", command=edit_expense, width=15).pack(side="left", padx=4)
tk.Button(buttons, text="DELETE SELECTED", command=delete_expense, width=15).pack(side="left", padx=4)
tk.Button(buttons, text="EXPORT CSV", command=export_csv, width=15).pack(side="left", padx=4)

toggle_button = tk.Button(buttons, text="🌙 Dark Mode", command=toggle_dark_mode, width=15)
toggle_button.pack(side="left", padx=4)

filter_frame = tk.Frame(root)
filter_frame.pack(pady=5)

tk.Label(filter_frame, text="🔍 Search:").pack(side="left", padx=4)
search_entry = tk.Entry(filter_frame, width=24)
search_entry.pack(side="left", padx=4)
search_entry.bind("<KeyRelease>", lambda event: refresh())

tk.Label(filter_frame, text="Month:").pack(side="left", padx=4)

# Month filter: choose a month from a specific year
current_year = date.today().year
months = ["All Months"] + [
    f"{calendar.month_name[m]} {year}"
    for year in range(current_year - 10, current_year + 11)
    for m in range(1, 13)
]

month_combo = ttk.Combobox(
    filter_frame, width=18, state="readonly", values=months
)
month_combo.set("All Months")
month_combo.pack(side="left", padx=4)
month_combo.bind("<<ComboboxSelected>>", lambda event: refresh())

tk.Button(filter_frame, text="CLEAR FILTER", command=clear_filter).pack(side="left", padx=5)

# Main content area
content = tk.Frame(root)
content.pack(pady=6)

table_frame = tk.Frame(content)
table_frame.grid(row=0, column=0, padx=8, sticky="n")

columns = ("Date","Category","Description","Amount")
expense_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=11)

for col in columns:
    expense_table.heading(col, text=col)

expense_table.column("Date", width=115)
expense_table.column("Category", width=120)
expense_table.column("Description", width=330)
expense_table.column("Amount", width=120)
expense_table.pack()

summary_frame = tk.Frame(content)
summary_frame.grid(row=0, column=1, padx=8, sticky="n")

tk.Label(summary_frame, text="CATEGORY SUMMARY",
         font=("Arial", 12, "bold")).pack(pady=3)

summary_tree = ttk.Treeview(
    summary_frame, columns=("Category","Amount"),
    show="headings", height=11
)
summary_tree.heading("Category", text="Category")
summary_tree.heading("Amount", text="Amount")
summary_tree.column("Category", width=130)
summary_tree.column("Amount", width=110)
summary_tree.pack()

chart_frame = tk.Frame(root)
chart_frame.pack(pady=5)

tk.Label(chart_frame, text="CATEGORY EXPENSE CHART",
         font=("Arial", 12, "bold")).pack()

chart = tk.Canvas(chart_frame, width=600, height=270, bg="white",
                  highlightthickness=1)
chart.pack()

root.protocol("WM_DELETE_WINDOW", close_app)

apply_theme()
refresh()
root.mainloop()
