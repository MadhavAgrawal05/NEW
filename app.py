import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="RetailIQ",
    page_icon="📊",
    layout="wide"
)

st.title("📊 RetailIQ")
st.caption("Intelligent Retail Analytics & DSA Optimization Platform")

# ---------------- LOAD DATASET ----------------
DATA_FILE = "store_sales_data (2).csv"


@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE)


try:
    df = load_data()
except Exception as e:
    st.error(f"Dataset load nahi hui: {e}")
    st.info(
        "Check karo ki store_sales_data (2).csv "
        "aur app.py same folder mein hain."
    )
    st.stop()

# ---------------- CLEAN COLUMN NAMES ----------------
df.columns = df.columns.astype(str).str.strip()


def normalize_name(name):
    """Ignore spaces, underscores and letter case."""
    return "".join(
        character.lower()
        for character in str(name)
        if character.isalnum()
    )


def find_column(possible_names):
    normalized_columns = {
        normalize_name(column): column
        for column in df.columns
    }

    for name in possible_names:
        key = normalize_name(name)
        if key in normalized_columns:
            return normalized_columns[key]

    return None


# Identify relevant columns
sales_col = find_column([
    "Sales", "Total Sales", "Revenue",
    "Sales Amount", "Total Revenue"
])

profit_col = find_column([
    "Profit", "Total Profit", "Profit Amount"
])

order_col = find_column([
    "Order ID", "OrderID", "Order Number"
])

state_col = find_column([
    "State", "Region", "State Name"
])

category_col = find_column([
    "Category", "Product Category",
    "Product Type", "Sub Category"
])

date_col = find_column([
    "Order Date", "Sales Date", "Date"
])

quantity_col = find_column([
    "Quantity", "Qty", "Units Sold"
])

# ---------------- DATA TYPE CONVERSION ----------------
for column in [sales_col, profit_col, quantity_col]:
    if column:
        df[column] = pd.to_numeric(
            df[column].astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        )

if date_col:
    df[date_col] = pd.to_datetime(
        df[date_col],
        errors="coerce",
        dayfirst=True
    )

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("🔎 Dashboard Filters")

filtered_df = df.copy()

if state_col:
    states = sorted(
        filtered_df[state_col].dropna().unique().tolist(),
        key=str
    )

    selected_states = st.sidebar.multiselect(
        "Select State",
        options=states,
        default=states
    )

    filtered_df = filtered_df[
        filtered_df[state_col].isin(selected_states)
    ]

if category_col:
    categories = sorted(
        filtered_df[category_col].dropna().unique().tolist(),
        key=str
    )

    selected_categories = st.sidebar.multiselect(
        "Select Category",
        options=categories,
        default=categories
    )

    filtered_df = filtered_df[
        filtered_df[category_col].isin(selected_categories)
    ]
# ---------------- SEPARATE START AND END DATE FILTERS ----------------
if date_col and filtered_df[date_col].notna().any():

    valid_dates = filtered_df[date_col].dropna()

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    st.sidebar.markdown("### 📅 Date Range Filter")

    st.sidebar.caption(
        f"Available dates: {min_date:%d-%m-%Y} to {max_date:%d-%m-%Y}"
    )

    # Start Date - separate input
    start_date = st.sidebar.date_input(
        "📅 Start Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="retailiq_start_date"
    )

    # End Date - separate input
    end_date = st.sidebar.date_input(
        "📅 End Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="retailiq_end_date"
    )

    if start_date > end_date:
        st.sidebar.error(
            "Start Date, End Date se aage nahi ho sakti."
        )
        st.stop()

    # Apply selected date range inclusively
    filtered_df = filtered_df[
        filtered_df[date_col].notna()
        & filtered_df[date_col].dt.date.between(
            start_date,
            end_date,
            inclusive="both"
        )
    ]

# ---------------- KPI CALCULATIONS ----------------
total_sales = (
    filtered_df[sales_col].sum()
    if sales_col else None
)

total_profit = (
    filtered_df[profit_col].sum()
    if profit_col else None
)

total_orders = (
    filtered_df[order_col].nunique()
    if order_col else len(filtered_df)
)

total_quantity = (
    filtered_df[quantity_col].sum()
    if quantity_col else None
)

if (
    sales_col
    and profit_col
    and total_sales is not None
    and total_sales != 0
):
    profit_margin = total_profit / total_sales * 100
else:
    profit_margin = None

# ---------------- KPI DASHBOARD ----------------
st.subheader("📈 Sales Overview")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Total Sales",
    f"₹{total_sales:,.0f}" if total_sales is not None else "N/A"
)

c2.metric(
    "Total Profit",
    f"₹{total_profit:,.0f}" if total_profit is not None else "N/A"
)

c3.metric("Total Orders", f"{total_orders:,}")

c4.metric(
    "Profit Margin",
    f"{profit_margin:.2f}%"
    if profit_margin is not None else "N/A"
)

c5.metric(
    "Quantity Sold",
    f"{total_quantity:,.0f}"
    if total_quantity is not None else "N/A"
)

st.caption(
    f"Showing {len(filtered_df):,} records "
    f"out of {len(df):,} total records."
)

# ---------------- SALES BY CATEGORY ----------------
left, right = st.columns(2)

with left:
    st.subheader("🛍️ Sales by Category")

    if category_col and sales_col:
        category_data = (
            filtered_df
            .groupby(category_col, as_index=False)[sales_col]
            .sum()
            .sort_values(sales_col, ascending=False)
        )

        fig = px.bar(
            category_data,
            x=category_col,
            y=sales_col,
            color=category_col,
            title="Category-wise Sales",
            labels={
                category_col: "Category",
                sales_col: "Sales (₹)"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(
            "Sales ya Category column identify nahi hui. "
            "Neeche Dataset Structure check karo."
        )

# ---------------- PROFIT BY STATE ----------------
with right:
    st.subheader("📍 Profit by State")

    if state_col and profit_col:
        state_data = (
            filtered_df
            .groupby(state_col, as_index=False)[profit_col]
            .sum()
            .sort_values(profit_col, ascending=False)
        )

        fig = px.bar(
            state_data,
            x=state_col,
            y=profit_col,
            color=state_col,
            title="State-wise Profit",
            labels={
                state_col: "State",
                profit_col: "Profit (₹)"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(
            "State ya Profit column identify nahi hui."
        )

# ---------------- MONTHLY SALES TREND ----------------
st.subheader("📅 Monthly Sales Trend")

if date_col and sales_col:
    trend_df = filtered_df.dropna(subset=[date_col]).copy()

    if not trend_df.empty:
        trend_df["Month"] = (
            trend_df[date_col]
            .dt.to_period("M")
            .astype(str)
        )

        monthly_sales = (
            trend_df
            .groupby("Month", as_index=False)[sales_col]
            .sum()
            .sort_values("Month")
        )

        fig = px.line(
            monthly_sales,
            x="Month",
            y=sales_col,
            markers=True,
            title="Monthly Sales Performance",
            labels={
                "Month": "Month",
                sales_col: "Sales (₹)"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Selected filters mein valid dates nahi hain.")

else:
    st.info(
        "Sales trend ke liye valid Date aur Sales columns chahiye."
    )

# ---------------- DATASET PREVIEW ----------------
with st.expander("📋 View Filtered Dataset"):
    st.dataframe(
        filtered_df,
        use_container_width=True
    )

# ---------------- DATASET STRUCTURE ----------------
with st.expander("🔍 Dataset Structure & Data Quality", expanded=True):
    st.write("**Actual Column Names:**")
    st.write(df.columns.tolist())

    st.write("**Data Types:**")
    st.dataframe(
        pd.DataFrame({
            "Column": df.columns,
            "Data Type": df.dtypes.astype(str).values,
            "Missing Values": df.isnull().sum().values
        }),
        use_container_width=True
    )

    st.write("**Detected Columns:**")
    st.json({
        "Sales": sales_col,
        "Profit": profit_col,
        "Order ID": order_col,
        "State": state_col,
        "Category": category_col,
        "Date": date_col,
        "Quantity": quantity_col
    })

# =====================================================
# CUSTOM HASH TABLE - ORDER ID SEARCH
# =====================================================

import time


class CustomHashTable:
    """Custom Hash Table using separate chaining."""

    def __init__(self, capacity=200003):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]
        self.size = 0

    def _hash(self, key):
        hash_value = 0

        for character in str(key):
            hash_value = (
                hash_value * 31 + ord(character)
            ) % self.capacity

        return hash_value

    def insert(self, key, value):
        key = str(key)
        bucket = self.buckets[self._hash(key)]

        for i, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                bucket[i] = (key, value)
                return

        bucket.append((key, value))
        self.size += 1

    def search(self, key):
        bucket = self.buckets[self._hash(str(key))]

        for stored_key, value in bucket:
            if stored_key == str(key):
                return value

        return None


@st.cache_resource
def build_order_hash_table(order_ids):
    table = CustomHashTable()

    for row_index, order_id in enumerate(order_ids):
        if pd.notna(order_id):
            table.insert(str(order_id), row_index)

    return table


# ---------------- ORDER SEARCH INTERFACE ----------------

st.divider()
st.header("⚡ DSA Explorer: Hash Table Search")

if order_col:
    order_ids = df[order_col].astype(str).tolist()
    hash_table = build_order_hash_table(tuple(order_ids))

    search_id = st.text_input(
        "Enter Order ID",
        value="ORD002917",
        key="hash_order_id"
    ).strip()

    if st.button("🔍 Search Order", key="hash_search_button"):

        start = time.perf_counter()
        row_index = hash_table.search(search_id)
        hash_time = time.perf_counter() - start

        start = time.perf_counter()

        linear_index = next(
            (
                i for i, order_id in enumerate(order_ids)
                if order_id == search_id
            ),
            None
        )

        linear_time = time.perf_counter() - start

        if row_index is not None:
            st.success("Order found successfully!")

            details = df.iloc[row_index]

            detail_columns = [
                order_col,
                sales_col,
                profit_col,
                state_col,
                category_col,
                quantity_col
            ]

            detail_columns = list(dict.fromkeys(
                col for col in detail_columns
                if col is not None
            ))

            st.subheader("📦 Order Details")
            st.dataframe(
                details[detail_columns].to_frame("Value"),
                use_container_width=True
            )

        else:
            st.warning("Order ID nahi mila. Koi valid ID try karo.")

        st.subheader("⏱️ Search Performance")

        c1, c2 = st.columns(2)

        c1.metric(
            "Custom Hash Table",
            f"{hash_time * 1000:.6f} ms"
        )

        c2.metric(
            "Linear Search",
            f"{linear_time * 1000:.6f} ms"
        )

        if hash_time > 0:
            st.metric(
                "Observed Speedup",
                f"{linear_time / hash_time:.2f}x"
            )

        st.caption(
            "Single-run timing hai; results fluctuate kar sakte hain. "
            "Repeated benchmarks hum Performance Lab mein add karenge."
        )

else:
    st.error("Order ID column identify nahi hui.")
    # ---------------- HASH TABLE PERFORMANCE LAB ----------------

st.divider()
st.header("🧪 Hash Table Performance Lab")

st.write(
    "Compare Custom Hash Table and Linear Search "
    "on datasets of different sizes."
)

if st.button("Run Performance Benchmark", key="run_hash_benchmark"):

    import time

    benchmark_sizes = [10000, 50000, 100000]
    results = []

    order_ids = df[order_col].dropna().astype(str).tolist()

    for size in benchmark_sizes:
        sample_ids = order_ids[:min(size, len(order_ids))]

        if not sample_ids:
            continue

        target_id = sample_ids[-1]

        # Build a hash table for this dataset size
        table = CustomHashTable(capacity=max(200003, size * 2))

        for index, order_id in enumerate(sample_ids):
            table.insert(order_id, index)

        # Repeat searches to reduce timing noise
        repetitions = 100

        start = time.perf_counter()
        for _ in range(repetitions):
            table.search(target_id)
        hash_ms = (time.perf_counter() - start) * 1000 / repetitions

        start = time.perf_counter()
        for _ in range(repetitions):
            next(
                (i for i, value in enumerate(sample_ids)
                 if value == target_id),
                None
            )
        linear_ms = (time.perf_counter() - start) * 1000 / repetitions

        results.append({
            "Dataset Size": len(sample_ids),
            "Hash Table (ms)": round(hash_ms, 6),
            "Linear Search (ms)": round(linear_ms, 6),
            "Speedup": round(linear_ms / hash_ms, 2)
            if hash_ms > 0 else None
        })

    results_df = pd.DataFrame(results)

    st.subheader("Benchmark Results")
    st.dataframe(results_df, use_container_width=True)

    st.subheader("Search Time Comparison")
    chart_df = results_df.set_index("Dataset Size")[
        ["Hash Table (ms)", "Linear Search (ms)"]
    ]
    st.bar_chart(chart_df)

    st.caption(
        "Results are averaged over 100 searches per dataset size. "
        "Actual timings depend on the system and dataset."
    )

    # ---------------- AVL TREE IMPLEMENTATION ----------------

class AVLNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


class AVLTree:
    def height(self, node):
        return node.height if node else 0

    def update_height(self, node):
        node.height = 1 + max(
            self.height(node.left),
            self.height(node.right)
        )

    def balance_factor(self, node):
        return (
            self.height(node.left) - self.height(node.right)
        ) if node else 0

    def rotate_right(self, y):
        x = y.left
        temp = x.right
        x.right = y
        y.left = temp
        self.update_height(y)
        self.update_height(x)
        return x

    def rotate_left(self, x):
        y = x.right
        temp = y.left
        y.left = x
        x.right = temp
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
            elif key < node.key:
                node = node.left
            else:
                node = node.right
        return None


# ---------------- AVL TREE DASHBOARD ----------------

st.divider()
st.header("🌳 DSA Explorer: AVL Tree Search")

if order_col:
    if st.button("Build AVL Tree", key="build_avl_tree"):
        avl = AVLTree()
        root = None

        with st.spinner("Building AVL Tree from Order IDs..."):
            for index, order_id in enumerate(
                df[order_col].dropna().astype(str)
            ):
                root = avl.insert(root, order_id, index)

        st.session_state["avl_tree"] = avl
        st.session_state["avl_root"] = root
        st.success("AVL Tree built successfully!")

    search_avl_id = st.text_input(
        "Enter Order ID to search in AVL Tree",
        value="ORD002917",
        key="avl_search_id"
    ).strip()

    if st.button("Search AVL Tree", key="search_avl_button"):
        if "avl_tree" not in st.session_state:
            st.warning("Pehle Build AVL Tree button click karo.")
        else:
            avl = st.session_state["avl_tree"]
            root = st.session_state["avl_root"]

            start = time.perf_counter()
            result_index = avl.search(root, search_avl_id)
            elapsed = (time.perf_counter() - start) * 1000

            if result_index is not None:
                st.success("Order found in AVL Tree!")
                details = df.iloc[result_index]
                detail_columns = [
                    order_col, sales_col, profit_col,
                    state_col, category_col, quantity_col
                ]
                detail_columns = list(dict.fromkeys(
                    col for col in detail_columns if col is not None
                ))
                st.dataframe(
                    details[detail_columns].to_frame("Value"),
                    use_container_width=True
                )
            else:
                st.warning("Order ID nahi mila.")

            st.metric("AVL Tree Search Time", f"{elapsed:.6f} ms")
else:
    st.error("Order ID column identify nahi hui.")

    # ---------------- HASH TABLE VS AVL TREE ----------------

st.divider()
st.header("⚖️ Hash Table vs AVL Tree")

st.write(
    "Compare both data structures using the same Order IDs "
    "and repeated search operations."
)

if st.button("Run Hash Table vs AVL Comparison",
             key="run_hash_avl_comparison"):

    import time
    import statistics

    ids = df[order_col].dropna().astype(str).tolist()
    ids = list(dict.fromkeys(ids))

    if not ids:
        st.warning("Dataset mein valid Order IDs nahi hain.")
    else:
        with st.spinner("Building both data structures..."):

            hash_table_compare = CustomHashTable(
                capacity=max(200003, len(ids) * 2)
            )
            avl_compare = AVLTree()
            avl_root_compare = None

            for index, order_id in enumerate(ids):
                hash_table_compare.insert(order_id, index)
                avl_root_compare = avl_compare.insert(
                    avl_root_compare, order_id, index
                )

        # Use the same existing IDs for both searches
        queries = ids[-min(100, len(ids)):]

        hash_times = []
        avl_times = []

        for query in queries:
            start = time.perf_counter()
            hash_table_compare.search(query)
            hash_times.append(
                (time.perf_counter() - start) * 1000
            )

            start = time.perf_counter()
            avl_compare.search(avl_root_compare, query)
            avl_times.append(
                (time.perf_counter() - start) * 1000
            )

        comparison_df = pd.DataFrame({
            "Metric": [
                "Unique Order IDs",
                "Search Queries",
                "Median Search Time (ms)",
                "Mean Search Time (ms)"
            ],
            "Custom Hash Table": [
                len(ids),
                len(queries),
                round(statistics.median(hash_times), 6),
                round(statistics.mean(hash_times), 6)
            ],
            "AVL Tree": [
                len(ids),
                len(queries),
                round(statistics.median(avl_times), 6),
                round(statistics.mean(avl_times), 6)
            ]
        })

        st.success("Comparison completed!")
        st.dataframe(comparison_df, use_container_width=True)

        chart_df = pd.DataFrame({
            "Data Structure": ["Hash Table", "AVL Tree"],
            "Median Search Time (ms)": [
                statistics.median(hash_times),
                statistics.median(avl_times)
            ]
        }).set_index("Data Structure")

        st.subheader("Median Search Time")
        st.bar_chart(chart_df)

        st.caption(
            "Both structures use the same unique Order IDs and queries. "
            "Construction time is excluded from search timing. "
            "Results may vary between runs."
        )

        # ---------------- FIBONACCI HEAP: INVENTORY PRIORITY ----------------

class FibNode:
    def __init__(self, key, item):
        self.key = key
        self.item = item
        self.parent = None
        self.child = None
        self.left = self
        self.right = self
        self.degree = 0
        self.mark = False


class FibonacciHeap:
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
        node = FibNode(float(key), item)
        self._add_to_root_list(node)
        self.total_nodes += 1
        return node

    def get_min(self):
        if self.minimum is None:
            return None
        return self.minimum.item, self.minimum.key

    def extract_min(self):
        z = self.minimum
        if z is None:
            return None

        if z.child is not None:
            children = []
            current = z.child
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
        roots = []
        current = self.minimum
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
            x = node
            degree = x.degree

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


# ---------------- INVENTORY PRIORITY DASHBOARD ----------------

st.divider()
st.header("🌿 DSA Explorer: Fibonacci Heap")
st.write(
    "Products with the lowest available quantity receive the "
    "highest priority for restocking."
)

if quantity_col and category_col:
    if st.button("Build Inventory Priority Queue",
                 key="build_fib_heap"):

        inventory_heap = FibonacciHeap()

        inventory_data = df[
            [category_col, quantity_col]
        ].copy()

        inventory_data[quantity_col] = pd.to_numeric(
            inventory_data[quantity_col], errors="coerce"
        )
        inventory_data = inventory_data.dropna(
            subset=[quantity_col]
        )

        for row_index, row in inventory_data.iterrows():
            inventory_heap.insert(
                row[quantity_col],
                {
                    "row_index": int(row_index),
                    "product": str(row[category_col]),
                    "quantity": float(row[quantity_col])
                }
            )

        st.session_state["inventory_heap"] = inventory_heap
        st.success(
            f"Priority queue built with {inventory_heap.total_nodes:,} records!"
        )

    if st.button("Show 10 Highest Restocking Priorities",
                 key="show_fib_priority"):

        if "inventory_heap" not in st.session_state:
            st.warning("Pehle Build Inventory Priority Queue click karo.")
        else:
            heap = st.session_state["inventory_heap"]
            priorities = []

            for _ in range(min(10, heap.total_nodes)):
                result = heap.extract_min()
                if result is None:
                    break

                item, quantity = result
                priorities.append({
                    "Product / Category": item["product"],
                    "Quantity": quantity,
                    "Priority": "High"
                })

            if priorities:
                st.dataframe(
                    pd.DataFrame(priorities),
                    use_container_width=True
                )
            else:
                st.info("Inventory queue empty hai.")
else:
    st.warning(
        "Dataset mein Quantity aur Category columns required hain."
    )

    # ---------------- FINAL DSA PERFORMANCE LAB ----------------

st.divider()
st.header("📊 Final DSA Performance Lab")

st.write(
    "Compare Hash Table, AVL Tree, and Fibonacci Heap "
    "using repeated search and priority extraction tests."
)

if st.button("Run Final DSA Evaluation", key="final_dsa_evaluation"):

    import time
    import statistics

    ids = df[order_col].dropna().astype(str).tolist()
    ids = list(dict.fromkeys(ids))

    if not ids:
        st.warning("No valid Order IDs found.")
    else:
        with st.spinner("Evaluating data structures..."):

            # Build Hash Table
            hash_eval = CustomHashTable(
                capacity=max(200003, len(ids) * 2)
            )

            start = time.perf_counter()
            for index, order_id in enumerate(ids):
                hash_eval.insert(order_id, index)
            hash_build_ms = (time.perf_counter() - start) * 1000

            # Build AVL Tree
            avl_eval = AVLTree()
            avl_root_eval = None

            start = time.perf_counter()
            for index, order_id in enumerate(ids):
                avl_root_eval = avl_eval.insert(
                    avl_root_eval, order_id, index
                )
            avl_build_ms = (time.perf_counter() - start) * 1000

            # Build Fibonacci Heap with quantity values
            fib_eval = FibonacciHeap()
            qty = pd.to_numeric(
                df[quantity_col], errors="coerce"
            ) if quantity_col else pd.Series(dtype=float)

            start = time.perf_counter()
            if quantity_col:
                for index, quantity in qty.items():
                    if pd.notna(quantity):
                        fib_eval.insert(
                            float(quantity),
                            {"row_index": int(index)}
                        )
            fib_build_ms = (time.perf_counter() - start) * 1000

            # Search same IDs in Hash Table and AVL Tree
            queries = ids[-min(100, len(ids)):]
            hash_times = []
            avl_times = []

            for query in queries:
                start = time.perf_counter()
                hash_eval.search(query)
                hash_times.append(
                    (time.perf_counter() - start) * 1000
                )

                start = time.perf_counter()
                avl_eval.search(avl_root_eval, query)
                avl_times.append(
                    (time.perf_counter() - start) * 1000
                )

            # One minimum extraction test for Fibonacci Heap
            fib_extract_ms = None
            if fib_eval.total_nodes > 0:
                start = time.perf_counter()
                fib_eval.get_min()
                fib_extract_ms = (
                    time.perf_counter() - start
                ) * 1000

        evaluation_df = pd.DataFrame([
            {
                "Data Structure": "Custom Hash Table",
                "Records": len(ids),
                "Build Time (ms)": round(hash_build_ms, 3),
                "Operation Tested": "Order ID Search",
                "Median Operation Time (ms)": round(
                    statistics.median(hash_times), 6
                )
            },
            {
                "Data Structure": "AVL Tree",
                "Records": len(ids),
                "Build Time (ms)": round(avl_build_ms, 3),
                "Operation Tested": "Order ID Search",
                "Median Operation Time (ms)": round(
                    statistics.median(avl_times), 6
                )
            },
            {
                "Data Structure": "Fibonacci Heap",
                "Records": fib_eval.total_nodes,
                "Build Time (ms)": round(fib_build_ms, 3),
                "Operation Tested": "Minimum Lookup",
                "Median Operation Time (ms)": round(
                    fib_extract_ms, 6
                ) if fib_extract_ms is not None else None
            }
        ])

        st.success("Evaluation completed!")
        st.dataframe(evaluation_df, use_container_width=True)
        st.download_button(
    label="📥 Download DSA Evaluation Results (CSV)",
    data=evaluation_df.to_csv(index=False).encode("utf-8"),
    file_name="retailiq_dsa_evaluation.csv",
    mime="text/csv"
)

        st.subheader("Construction Time Comparison")
        build_chart = evaluation_df.set_index("Data Structure")[
            ["Build Time (ms)"]
        ]
        st.bar_chart(build_chart)

        st.caption(
            "Hash Table and AVL Tree use the same Order IDs and search queries. "
            "Fibonacci Heap is evaluated on minimum lookup, a different operation, "
            "so its operation time should not be directly compared with search times. "
            "Build times depend on hardware and dataset order."
        )
