import time
import statistics
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="RetailIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep sidebar visible (Streamlit/browser behavior can vary by version)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 260px !important;
        width: 260px !important;
        visibility: visible !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 260px !important;
    }
    [data-testid="stSidebarCollapse"],
    [data-testid="stSidebar"] button[kind="header"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- LOAD DATA ----------------
DATA_FILE = "store_sales_data (2).csv"

@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE)

try:
    df = load_data()
except Exception as exc:
    st.error(f"Dataset load nahi hui: {exc}")
    st.info("Ensure karo ki store_sales_data (2).csv aur app.py same folder mein hain.")
    st.stop()

df.columns = df.columns.astype(str).str.strip()

def normalize_name(name):
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())

def find_column(possible_names):
    normalized = {normalize_name(col): col for col in df.columns}
    for name in possible_names:
        if normalize_name(name) in normalized:
            return normalized[normalize_name(name)]
    return None

sales_col = find_column(["Sales", "Total Sales", "Revenue", "Sales Amount", "Total Revenue"])
profit_col = find_column(["Profit", "Total Profit", "Profit Amount"])
order_col = find_column(["Order ID", "OrderID", "Order Number"])
state_col = find_column(["State", "Region", "State Name"])
category_col = find_column(["Category", "Product Category", "Product Type", "Sub Category"])
date_col = find_column(["Order Date", "Sales Date", "Date"])
quantity_col = find_column(["Quantity", "Qty", "Units Sold"])

for col in [sales_col, profit_col, quantity_col]:
    if col:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

# ---------------- DATA STRUCTURES ----------------
class CustomHashTable:
    """Hash table with separate chaining."""
    def __init__(self, capacity=200003):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]
        self.size = 0

    def _hash(self, key):
        value = 0
        for char in str(key):
            value = (value * 31 + ord(char)) % self.capacity
        return value

    def insert(self, key, value):
        key = str(key)
        bucket = self.buckets[self._hash(key)]
        for i, (old_key, _) in enumerate(bucket):
            if old_key == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self.size += 1

    def search(self, key):
        key = str(key)
        for old_key, value in self.buckets[self._hash(key)]:
            if old_key == key:
                return value
        return None

@st.cache_resource
def build_order_hash_table(order_ids):
    table = CustomHashTable()
    for row_index, order_id in enumerate(order_ids):
        if pd.notna(order_id) and str(order_id).lower() != "nan":
            table.insert(str(order_id), row_index)
    return table

class AVLNode:
    def __init__(self, key, value):
        self.key, self.value = key, value
        self.left = self.right = None
        self.height = 1

class AVLTree:
    def height(self, node):
        return node.height if node else 0

    def update_height(self, node):
        node.height = 1 + max(self.height(node.left), self.height(node.right))

    def balance_factor(self, node):
        return self.height(node.left) - self.height(node.right) if node else 0

    def rotate_right(self, y):
        x, temp = y.left, y.left.right
        x.right, y.left = y, temp
        self.update_height(y)
        self.update_height(x)
        return x

    def rotate_left(self, x):
        y, temp = x.right, x.right.left
        y.left, x.right = x, temp
        self.update_height(x)
        self.update_height(y)
        return y

    def insert(self, node, key, value):
        if node is None:
            return AVLNode(key, value)
        if key < node.key:
            node.left = self.insert(node.left, key, value)
        elif key > node.key:
            node.right = self.insert(node.right, key, value)
        else:
            node.value = value
            return node
        self.update_height(node)
        balance = self.balance_factor(node)
        if balance > 1 and key < node.left.key:
            return self.rotate_right(node)
        if balance < -1 and key > node.right.key:
            return self.rotate_left(node)
        if balance > 1 and key > node.left.key:
            node.left = self.rotate_left(node.left)
            return self.rotate_right(node)
        if balance < -1 and key < node.right.key:
            node.right = self.rotate_right(node.right)
            return self.rotate_left(node)
        return node

    def search(self, node, key):
        while node:
            if key == node.key:
                return node.value
            node = node.left if key < node.key else node.right
        return None

class FibNode:
    def __init__(self, key, item):
        self.key, self.item = float(key), item
        self.parent = self.child = None
        self.left = self.right = self
        self.degree = 0
        self.mark = False

class FibonacciHeap:
    """Min Fibonacci heap supporting insert, get-min and extract-min."""
    def __init__(self):
        self.minimum = None
        self.total_nodes = 0

    def _add_to_root_list(self, node):
        node.parent = None
        if self.minimum is None:
            node.left = node.right = node
            self.minimum = node
        else:
            node.left = self.minimum
            node.right = self.minimum.right
            self.minimum.right.left = node
            self.minimum.right = node
            if node.key < self.minimum.key:
                self.minimum = node

    def insert(self, key, item):
        node = FibNode(key, item)
        self._add_to_root_list(node)
        self.total_nodes += 1
        return node

    def get_min(self):
        return (self.minimum.item, self.minimum.key) if self.minimum else None

    def extract_min(self):
        z = self.minimum
        if z is None:
            return None
        if z.child is not None:
            children, current = [], z.child
            while True:
                children.append(current)
                current = current.right
                if current == z.child:
                    break
            for child in children:
                child.left.right = child.right
                child.right.left = child.left
                child.left = child.right = child
                self._add_to_root_list(child)
        if z.right == z:
            self.minimum = None
        else:
            z.left.right = z.right
            z.right.left = z.left
            self.minimum = z.right
        self.total_nodes -= 1
        if self.minimum is not None:
            self._consolidate()
        return z.item, z.key

    def _consolidate(self):
        roots, current = [], self.minimum
        while True:
            roots.append(current)
            current = current.right
            if current == self.minimum:
                break
        for node in roots:
            node.left.right = node.right
            node.right.left = node.left
            node.left = node.right = node
        self.minimum = None
        degree_table = {}

        def link(child, parent):
            child.left.right = child.right
            child.right.left = child.left
            child.parent = parent
            child.left = child.right = child
            if parent.child is None:
                parent.child = child
            else:
                child.left = parent.child
                child.right = parent.child.right
                parent.child.right.left = child
                parent.child.right = child
            parent.degree += 1
            child.mark = False

        for node in roots:
            x, degree = node, node.degree
            while degree in degree_table:
                y = degree_table.pop(degree)
                if y.key < x.key:
                    x, y = y, x
                link(y, x)
                degree = x.degree
            degree_table[degree] = x
        for node in degree_table.values():
            node.left = node.right = node
            self._add_to_root_list(node)

def order_details(row_index):
    wanted = [order_col, sales_col, profit_col, state_col, category_col, quantity_col]
    wanted = list(dict.fromkeys(col for col in wanted if col is not None))
    st.dataframe(df.iloc[row_index][wanted].to_frame("Value"), use_container_width=True)

# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.markdown("## 📊 RetailIQ")
st.sidebar.caption("RETAIL ANALYTICS & DSA")
st.sidebar.divider()
page = st.sidebar.radio(
    "NAVIGATION",
    [
        "🏠 Sales Dashboard",
        "🔎 Order Search",
        "🧪 Hash Table Lab",
        "🌳 AVL Tree Lab",
        "🌿 Fibonacci Heap",
        "📊 Performance Lab",
        "🗂️ Dataset & Quality",
    ],
)
st.sidebar.divider()

# ---------------- SINGLE DATA FILTER SECTION ----------------
st.sidebar.markdown("### 🎛️ Data Filters")
st.sidebar.caption("Filter your retail data")
filtered_df = df.copy()
states = sorted(df[state_col].dropna().unique().tolist(), key=str) if state_col else []
categories = sorted(df[category_col].dropna().unique().tolist(), key=str) if category_col else []
if date_col and df[date_col].notna().any():
    min_date, max_date = df[date_col].min().date(), df[date_col].max().date()
else:
    min_date = max_date = None

def reset_filters():
    for key in ["filter_state", "filter_category", "filter_start_date", "filter_end_date"]:
        st.session_state.pop(key, None)

if state_col:
    selected_state = st.sidebar.selectbox("📍 State", ["All States"] + states, key="filter_state")
    if selected_state != "All States":
        filtered_df = filtered_df[filtered_df[state_col] == selected_state]

if category_col:
    selected_category = st.sidebar.selectbox("🛍️ Category", ["All Categories"] + categories, key="filter_category")
    if selected_category != "All Categories":
        filtered_df = filtered_df[filtered_df[category_col] == selected_category]

if min_date is not None and max_date is not None:
    st.sidebar.markdown("**📅 Date Range**")
    start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date, key="filter_start_date")
    end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date, key="filter_end_date")
    if start_date > end_date:
        st.sidebar.error("Start Date must be before End Date.")
        filtered_df = filtered_df.iloc[0:0]
    else:
        filtered_df = filtered_df[filtered_df[date_col].dt.date.between(start_date, end_date)]

st.sidebar.button("↩ Reset All Filters", on_click=reset_filters, use_container_width=True)
st.sidebar.divider()
st.sidebar.metric("Filtered Records", f"{len(filtered_df):,}")
st.sidebar.caption(f"Total dataset records: {len(df):,}")

# ---------------- SALES DASHBOARD ----------------
if page == "🏠 Sales Dashboard":
    st.title("📊 RetailIQ")
    st.caption("Intelligent Retail Analytics & DSA Optimization Platform")
    st.subheader("📈 Sales Overview")
    total_sales = filtered_df[sales_col].sum() if sales_col else None
    total_profit = filtered_df[profit_col].sum() if profit_col else None
    total_orders = filtered_df[order_col].nunique() if order_col else len(filtered_df)
    total_quantity = filtered_df[quantity_col].sum() if quantity_col else None
    profit_margin = total_profit / total_sales * 100 if sales_col and profit_col and total_sales else None
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Sales", f"₹{total_sales:,.0f}" if total_sales is not None else "N/A")
    c2.metric("Total Profit", f"₹{total_profit:,.0f}" if total_profit is not None else "N/A")
    c3.metric("Total Orders", f"{total_orders:,}")
    c4.metric("Profit Margin", f"{profit_margin:.2f}%" if profit_margin is not None else "N/A")
    c5.metric("Quantity Sold", f"{total_quantity:,.0f}" if total_quantity is not None else "N/A")
    st.caption(f"Showing {len(filtered_df):,} filtered rows out of {len(df):,}.")
    left, right = st.columns(2)
    with left:
        st.subheader("🛍️ Sales by Category")
        if category_col and sales_col:
            category_data = filtered_df.groupby(category_col, as_index=False)[sales_col].sum().sort_values(sales_col, ascending=False)
            fig = px.bar(category_data, x=category_col, y=sales_col, color=category_col, labels={category_col: "Category", sales_col: "Sales (₹)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Sales/Category column identify nahi hui.")
    with right:
        st.subheader("📍 Profit by State")
        if state_col and profit_col:
            state_data = filtered_df.groupby(state_col, as_index=False)[profit_col].sum().sort_values(profit_col, ascending=False)
            fig = px.bar(state_data, x=state_col, y=profit_col, color=state_col, labels={state_col: "State", profit_col: "Profit (₹)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("State/Profit column identify nahi hui.")
    st.subheader("📅 Monthly Sales Trend")
    if date_col and sales_col:
        trend = filtered_df.dropna(subset=[date_col]).copy()
        if not trend.empty:
            trend["Month"] = trend[date_col].dt.to_period("M").astype(str)
            monthly = trend.groupby("Month", as_index=False)[sales_col].sum().sort_values("Month")
            fig = px.line(monthly, x="Month", y=sales_col, markers=True, labels={"Month": "Month", sales_col: "Sales (₹)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selected filters mein valid dates nahi hain.")
    else:
        st.info("Monthly trend ke liye Date aur Sales columns chahiye.")

# ---------------- ORDER SEARCH ----------------
elif page == "🔎 Order Search":
    st.title("🔎 Order Search")
    st.caption("Search an order and compare Hash Table lookup with Linear Search.")
    if not order_col:
        st.error("Order ID column identify nahi hui.")
    else:
        order_ids = df[order_col].astype(str).tolist()
        table = build_order_hash_table(tuple(order_ids))
        search_id = st.text_input("Enter Order ID", placeholder="e.g. ORD002917", key="order_search_page").strip()
        if st.button("Search Order", type="primary"):
            start = time.perf_counter()
            row_index = table.search(search_id)
            hash_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            linear_index = next((i for i, value in enumerate(order_ids) if value == search_id), None)
            linear_ms = (time.perf_counter() - start) * 1000
            if row_index is not None:
                st.success("Order found.")
                order_details(row_index)
            else:
                st.warning("Order ID nahi mila. ID spelling check karo.")
            a, b = st.columns(2)
            a.metric("Hash Table Search", f"{hash_ms:.6f} ms")
            b.metric("Linear Search", f"{linear_ms:.6f} ms")
            st.caption("Single-run timings fluctuate kar sakti hain; benchmark page par repeated tests hain.")

# ---------------- HASH TABLE LAB ----------------
elif page == "🧪 Hash Table Lab":
    st.title("🧪 Hash Table Performance Lab")
    st.write("Custom Hash Table aur Linear Search ko different dataset sizes par compare karo.")
    if not order_col:
        st.error("Order ID column identify nahi hui.")
    elif st.button("▶ Run Benchmark", type="primary"):
        ids = df[order_col].dropna().astype(str).tolist()
        results = []
        for size in [10000, 50000, 100000]:
            sample = ids[:min(size, len(ids))]
            if not sample:
                continue
            table = CustomHashTable(max(200003, len(sample) * 2))
            for i, value in enumerate(sample):
                table.insert(value, i)
            target, repeats = sample[-1], 100
            start = time.perf_counter()
            for _ in range(repeats):
                table.search(target)
            hash_ms = (time.perf_counter() - start) * 1000 / repeats
            start = time.perf_counter()
            for _ in range(repeats):
                next((i for i, value in enumerate(sample) if value == target), None)
            linear_ms = (time.perf_counter() - start) * 1000 / repeats
            results.append({"Dataset Size": len(sample), "Hash Table (ms)": hash_ms, "Linear Search (ms)": linear_ms})
        result_df = pd.DataFrame(results)
        st.dataframe(result_df.round(6), use_container_width=True)
        if not result_df.empty:
            st.bar_chart(result_df.set_index("Dataset Size"))
            st.download_button("📥 Download benchmark CSV", result_df.to_csv(index=False).encode("utf-8"), "hash_table_benchmark.csv", "text/csv")

# ---------------- AVL TREE LAB ----------------
elif page == "🌳 AVL Tree Lab":
    st.title("🌳 AVL Tree Search")
    st.write("Build an AVL Tree from Order IDs, then search an order.")
    if not order_col:
        st.error("Order ID column identify nahi hui.")
    else:
        if st.button("Build AVL Tree", type="primary"):
            ids = df[order_col].dropna().astype(str).tolist()
            tree, root = AVLTree(), None
            with st.spinner("Building AVL Tree..."):
                for i, value in enumerate(ids):
                    root = tree.insert(root, value, i)
            st.session_state["avl_tree"] = tree
            st.session_state["avl_root"] = root
            st.success(f"AVL Tree built with {len(ids):,} records.")
        search_id = st.text_input("Enter Order ID", placeholder="e.g. ORD002917", key="avl_search_page").strip()
        if st.button("Search AVL Tree"):
            if "avl_tree" not in st.session_state:
                st.warning("Pehle Build AVL Tree click karo.")
            else:
                start = time.perf_counter()
                idx = st.session_state["avl_tree"].search(st.session_state["avl_root"], search_id)
                elapsed = (time.perf_counter() - start) * 1000
                if idx is not None:
                    st.success("Order found.")
                    order_details(idx)
                else:
                    st.warning("Order ID nahi mila.")
                st.metric("AVL Search Time", f"{elapsed:.6f} ms")

# ---------------- FIBONACCI HEAP ----------------
elif page == "🌿 Fibonacci Heap":
    st.title("🌿 Fibonacci Heap Priority Queue")
    st.info("Quantity/Units Sold actual stock level nahi hota. Demo mein lowest quantity ko priority example ke roop mein use kiya gaya hai.")
    if not quantity_col or not category_col:
        st.warning("Quantity aur Category columns required hain.")
    else:
        if st.button("Build Priority Queue", type="primary"):
            heap = FibonacciHeap()
            data = df[[category_col, quantity_col]].dropna(subset=[quantity_col])
            for idx, row in data.iterrows():
                heap.insert(row[quantity_col], {"row_index": int(idx), "category": str(row[category_col]), "quantity": float(row[quantity_col])})
            st.session_state["fib_heap"] = heap
            st.success(f"Priority queue built with {heap.total_nodes:,} records.")
        if st.button("Show 10 Lowest Quantity Records"):
            if "fib_heap" not in st.session_state:
                st.warning("Pehle Build Priority Queue click karo.")
            else:
                heap = st.session_state["fib_heap"]
                output = []
                for _ in range(min(10, heap.total_nodes)):
                    item = heap.extract_min()
                    if item is None:
                        break
                    record, quantity = item
                    output.append({"Category": record["category"], "Quantity": quantity, "Priority": "High"})
                if output:
                    st.dataframe(pd.DataFrame(output), use_container_width=True)
                else:
                    st.info("Queue empty hai. Dobara build karo.")

# ---------------- PERFORMANCE LAB ----------------
elif page == "📊 Performance Lab":
    st.title("📊 DSA Performance Lab")
    st.write("Hash Table, AVL Tree aur Fibonacci Heap ke build/operation times ka summary.")
    if st.button("▶ Run Final Evaluation", type="primary"):
        if not order_col:
            st.error("Order ID column identify nahi hui.")
        else:
            ids = list(dict.fromkeys(df[order_col].dropna().astype(str).tolist()))
            if not ids:
                st.warning("No valid Order IDs found.")
            else:
                hash_table = CustomHashTable(max(200003, len(ids) * 2))
                start = time.perf_counter()
                for i, value in enumerate(ids):
                    hash_table.insert(value, i)
                hash_build = (time.perf_counter() - start) * 1000
                tree, root = AVLTree(), None
                start = time.perf_counter()
                for i, value in enumerate(ids):
                    root = tree.insert(root, value, i)
                avl_build = (time.perf_counter() - start) * 1000
                queries = ids[-min(100, len(ids)):]
                hash_times, avl_times = [], []
                for query in queries:
                    start = time.perf_counter()
                    hash_table.search(query)
                    hash_times.append((time.perf_counter() - start) * 1000)
                    start = time.perf_counter()
                    tree.search(root, query)
                    avl_times.append((time.perf_counter() - start) * 1000)
                fib, fib_build, fib_count = FibonacciHeap(), 0.0, 0
                if quantity_col:
                    quantities = pd.to_numeric(df[quantity_col], errors="coerce")
                    start = time.perf_counter()
                    for idx, qty in quantities.items():
                        if pd.notna(qty):
                            fib.insert(float(qty), {"row_index": int(idx)})
                            fib_count += 1
                    fib_build = (time.perf_counter() - start) * 1000
                min_ms = None
                if fib_count:
                    start = time.perf_counter()
                    fib.get_min()
                    min_ms = (time.perf_counter() - start) * 1000
                evaluation = pd.DataFrame([
                    {"Data Structure": "Custom Hash Table", "Records": len(ids), "Build Time (ms)": round(hash_build, 3), "Operation": "Order ID Search", "Median Operation Time (ms)": round(statistics.median(hash_times), 6)},
                    {"Data Structure": "AVL Tree", "Records": len(ids), "Build Time (ms)": round(avl_build, 3), "Operation": "Order ID Search", "Median Operation Time (ms)": round(statistics.median(avl_times), 6)},
                    {"Data Structure": "Fibonacci Heap", "Records": fib_count, "Build Time (ms)": round(fib_build, 3), "Operation": "Minimum Lookup", "Median Operation Time (ms)": round(min_ms, 6) if min_ms is not None else None},
                ])
                st.success("Evaluation complete.")
                st.dataframe(evaluation, use_container_width=True)
                st.download_button("📥 Download Evaluation CSV", evaluation.to_csv(index=False).encode("utf-8"), "retailiq_dsa_evaluation.csv", "text/csv")
                st.subheader("Build Time Comparison")
                st.bar_chart(evaluation.set_index("Data Structure")[["Build Time (ms)"]])
                st.caption("Fibonacci Heap ka minimum lookup, Hash Table/AVL ke search operation se different hai; timings directly compare na karein.")

# ---------------- DATASET & QUALITY ----------------
elif page == "🗂️ Dataset & Quality":
    st.title("🗂️ Dataset & Data Quality")
    st.write(f"**Rows:** {len(df):,} | **Columns:** {len(df.columns):,}")
    with st.expander("Preview filtered dataset", expanded=True):
        st.dataframe(filtered_df.head(100), use_container_width=True)
    quality = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isnull().sum().values,
        "Missing (%)": (df.isnull().mean().values * 100).round(2),
    })
    st.subheader("Data Quality Report")
    st.dataframe(quality, use_container_width=True)
    st.subheader("Detected Columns")
    st.json({"Sales": sales_col, "Profit": profit_col, "Order ID": order_col, "State": state_col, "Category": category_col, "Date": date_col, "Quantity": quantity_col})
    st.download_button("📥 Download filtered data CSV", filtered_df.to_csv(index=False).encode("utf-8"), "retailiq_filtered_data.csv", "text/csv")

st.divider()
st.caption("RetailIQ · Interactive Retail Analytics & DSA Optimization Platform")
