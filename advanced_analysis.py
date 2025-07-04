import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pathlib import Path
from scipy import stats

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------
CLEAN_DATA_DIR = Path("cleaned_data")
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="white")

# ---------------------------------------------------------------
# Helper loader
# ---------------------------------------------------------------

def _load_clean(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = CLEAN_DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Required dataset '{name}' not found in {CLEAN_DATA_DIR}.")
    return pd.read_csv(path, parse_dates=parse_dates)

# ---------------------------------------------------------------
# 1. Identify inefficient routes (high cost & high delay)
# ---------------------------------------------------------------

def inefficient_routes(shipments_df: pd.DataFrame, delays_df: pd.DataFrame) -> pd.DataFrame:
    """Return routes where average cost & average delay exceed the 75th percentile for each metric."""
    # Average cost per route
    cost_agg = shipments_df.groupby("route_id")["cost"].mean().rename("avg_cost")
    # Average delay per route
    delay_agg = delays_df.groupby("route_id")["delay_hours"].mean().rename("avg_delay")

    combined = (
        pd.concat([cost_agg, delay_agg], axis=1)
        .dropna()
        .reset_index()
    )

    cost_thresh = combined["avg_cost"].quantile(0.75)
    delay_thresh = combined["avg_delay"].quantile(0.75)

    ineff = combined[(combined["avg_cost"] > cost_thresh) & (combined["avg_delay"] > delay_thresh)]
    ineff = ineff.sort_values(["avg_cost", "avg_delay"], ascending=False)

    out_csv = OUTPUT_DIR / "inefficient_routes.csv"
    ineff.to_csv(out_csv, index=False)
    print(f"🚨 Inefficient routes saved → {out_csv} (n={len(ineff)})")
    return ineff

# ---------------------------------------------------------------
# 2. Correlation analysis
# ---------------------------------------------------------------

def correlation_analysis(shipments_df: pd.DataFrame, routes_df: pd.DataFrame):
    """Compute correlation matrix for selected metrics and save heatmap."""
    # Merge distance into shipments
    merged = shipments_df.merge(routes_df[["route_id", "distance"]], on="route_id", how="left")

    merged = merged.dropna(subset=["cost", "weight", "distance"])

    # Compute transit time per shipment
    merged["transit_hours"] = (
        pd.to_datetime(merged["delivery_date"]) - pd.to_datetime(merged["ship_date"])
    ).dt.total_seconds() / 3600

    metrics = merged[["weight", "cost", "distance", "transit_hours"]]
    corr = metrics.corr(method="pearson")

    # Plot heatmap
    plt.figure(figsize=(6, 4))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Correlation matrix of key logistics metrics")
    plt.tight_layout()

    file_path = PLOTS_DIR / "correlation_heatmap.png"
    plt.savefig(file_path, dpi=120)
    plt.close()
    print(f"📊 Correlation heatmap saved → {file_path}")

# ---------------------------------------------------------------
# 3. Sankey diagram of cargo flows
# ---------------------------------------------------------------

def sankey_cargo_flow(shipments_df: pd.DataFrame, routes_df: pd.DataFrame):
    """Create a Sankey diagram of cargo flows between origin and destination regions."""
    route_meta = routes_df[["route_id", "origin", "destination"]]
    flows = (
        shipments_df.merge(route_meta, on="route_id", how="left")
        .groupby(["origin", "destination"])
        .size()
        .reset_index(name="count")
    )

    # Build node list
    nodes = list(pd.unique(flows[["origin", "destination"]].values.ravel()))
    node_indices = {node: i for i, node in enumerate(nodes)}

    # Build links
    link_source = flows["origin"].map(node_indices)
    link_target = flows["destination"].map(node_indices)
    link_value = flows["count"]

    sankey_fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=nodes, pad=15, thickness=20, color="rgba(63,81,181,0.8)"),
                link=dict(source=link_source, target=link_target, value=link_value),
            )
        ]
    )
    sankey_fig.update_layout(title_text="Cargo flow between origins and destinations", font_size=10)

    html_path = PLOTS_DIR / "cargo_flow_sankey.html"
    sankey_fig.write_html(html_path)
    print(f"🌐 Sankey diagram saved → {html_path}")

# ---------------------------------------------------------------
# 4. Statistical hypothesis testing
# ---------------------------------------------------------------

def hypothesis_testing(shipments_df: pd.DataFrame):
    """ANOVA/Kruskal test to check if delivery times differ across carriers."""
    if "carrier_id" not in shipments_df.columns:
        print("carrier_id column missing: cannot run hypothesis testing.")
        return

    shipments_df = shipments_df.dropna(subset=["carrier_id", "ship_date", "delivery_date"]).copy()
    shipments_df["transit_hours"] = (
        pd.to_datetime(shipments_df["delivery_date"]) - pd.to_datetime(shipments_df["ship_date"])
    ).dt.total_seconds() / 3600

    # Filter carriers with at least 30 shipments to have enough samples
    carrier_counts = shipments_df["carrier_id"].value_counts()
    valid_carriers = carrier_counts[carrier_counts >= 30].index.tolist()
    data = [
        shipments_df.loc[shipments_df["carrier_id"] == cid, "transit_hours"].values
        for cid in valid_carriers
    ]

    if len(data) < 2:
        print("Not enough carriers with sample size >=30 for hypothesis test.")
        return

    # Use Kruskal-Wallis (non-parametric ANOVA alternative)
    stat, pval = stats.kruskal(*data)
    print("\n📈 Hypothesis Test (Kruskal-Wallis)")
    print("H0: No difference in delivery times across carriers")
    print(f"Statistic = {stat:.3f}, p-value = {pval:.4f}")
    interpretation = "Reject H0" if pval < 0.05 else "Fail to reject H0"
    print(f"Result: {interpretation} at α=0.05\n")

    # Save summary to text file
    summary_text = (
        "Kruskal-Wallis test across carriers (n≥30 shipments)\n"
        f"Statistic: {stat:.3f}\n"
        f"p-value : {pval:.4f}\n"
        f"Decision: {interpretation}\n"
    )
    summary_path = OUTPUT_DIR / "delivery_time_hypothesis_test.txt"
    with open(summary_path, "w") as f:
        f.write(summary_text)
    print(f"📝 Hypothesis test summary saved → {summary_path}")

# ---------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------

def main():
    print("\n⏳ Loading cleaned datasets...")
    shipments_df = _load_clean("shipments_clean.csv", parse_dates=["ship_date", "delivery_date"])
    delays_df = _load_clean("delays_clean.csv", parse_dates=["date"])
    routes_df = _load_clean("routes_clean.csv")

    # 1. Inefficient routes
    ineff_df = inefficient_routes(shipments_df, delays_df)

    # 2. Correlation analysis
    correlation_analysis(shipments_df, routes_df)

    # 3. Sankey diagram
    sankey_cargo_flow(shipments_df, routes_df)

    # 4. Hypothesis testing
    hypothesis_testing(shipments_df)

    print("✔️ Advanced analysis complete.")


if __name__ == "__main__":
    main()