import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------
CLEAN_DATA_DIR = Path("cleaned_data")
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="ticks")

# ---------------------------------------------------------------
# Load & prepare data
# ---------------------------------------------------------------
routes_path = CLEAN_DATA_DIR / "routes_clean.csv"
if not routes_path.exists():
    raise FileNotFoundError("Cleaned routes data not found. Run data_cleaning.py first.")

routes_df = pd.read_csv(routes_path)

# Ensure required numeric columns exist
feature_cols = ["distance", "avg_time", "avg_cost"]
missing_feats = [c for c in feature_cols if c not in routes_df.columns]
if missing_feats:
    raise KeyError(f"Missing expected feature columns in routes data: {missing_feats}")

# Drop rows with any NA in feature columns
routes_df = routes_df.dropna(subset=feature_cols).copy()

# Standardize features
scaler = StandardScaler()
scaled_features = scaler.fit_transform(routes_df[feature_cols])

# ---------------------------------------------------------------
# KMeans clustering
# ---------------------------------------------------------------
N_CLUSTERS = 3
kmeans = KMeans(n_clusters=N_CLUSTERS, n_init=10, random_state=42)
routes_df["cluster"] = kmeans.fit_predict(scaled_features)

# ---------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------
plt.figure(figsize=(10, 6))
sns.scatterplot(
    data=routes_df,
    x="distance",
    y="avg_time",
    hue="cluster",
    palette="Set2",
    size="avg_cost",
    sizes=(20, 200),
    alpha=0.8,
)
plt.title("KMeans clusters of routes (distance vs. avg_time, size ~ avg_cost)")
plt.xlabel("Distance (km)")
plt.ylabel("Average travel time (hours)")
plt.legend(title="Cluster")
plt.tight_layout()

plot_file = PLOTS_DIR / "route_clusters.png"
plt.savefig(plot_file, dpi=120)
plt.close()
print(f"📊 Cluster scatter plot saved → {plot_file}")

# ---------------------------------------------------------------
# Cluster profiles
# ---------------------------------------------------------------
cluster_profile = (
    routes_df.groupby("cluster")[feature_cols]
    .mean()
    .round(2)
    .reset_index()
)

profile_csv = OUTPUT_DIR / "cluster_profiles.csv"
cluster_profile.to_csv(profile_csv, index=False)
print(f"📄 Cluster profiles saved → {profile_csv}\n")
print(cluster_profile)