"""
Exploratory Data Analysis & Clustering for Detector Dataset
-----------------------------------------------------------
Loads 45_augmented.csv, visualizes numeric distributions, correlations,
and performs KMeans clustering on scaled numeric features.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. LOAD DATA
# ============================================================
df = pd.read_csv(r"D:\ED\LGBM\45_augmented.csv")
print(f"Dataset shape: {df.shape}")
print(df.info())
print(df.head())

# Drop 'RuleExplanation' if present
if 'RuleExplanation' in df.columns:
    df = df.drop(columns=['RuleExplanation'])

# Identify column types
categorical_cols = ['HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay', 'SafetyLabel']
numeric_cols = ['ED', 'ED_raw', 'DurationMins', 'Age', 'RiskScore']

# Check that all columns exist
for col in categorical_cols + numeric_cols:
    if col not in df.columns:
        print(f"Warning: {col} not found in dataset.")
        # remove from list if missing
        if col in categorical_cols:
            categorical_cols.remove(col)
        elif col in numeric_cols:
            numeric_cols.remove(col)

print(f"\nNumeric columns: {numeric_cols}")
print(f"Categorical columns: {categorical_cols}")

# ============================================================
# 2. SUMMARY STATISTICS
# ============================================================
print("\n" + "="*50)
print("NUMERIC DESCRIPTIVE STATISTICS")
print("="*50)
print(df[numeric_cols].describe())

print("\n" + "="*50)
print("CATEGORICAL DISTRIBUTIONS")
print("="*50)
for col in categorical_cols:
    print(f"\n{col}:\n{df[col].value_counts()}")

# ============================================================
# 3. VISUALIZATIONS
# ============================================================
plt.style.use('seaborn-v0_8-whitegrid')
fig = plt.figure(figsize=(16, 12))

# 3.1 Histograms for numeric features
for i, col in enumerate(numeric_cols, 1):
    plt.subplot(2, 3, i)
    sns.histplot(df[col], kde=True, bins=30, color='steelblue')
    plt.title(f'Distribution of {col}')
plt.tight_layout()
plt.savefig('histograms.png', dpi=150)
plt.show()

# 3.2 Pairplot for numeric features (colored by SafetyLabel)
sns.pairplot(df, vars=numeric_cols, hue='SafetyLabel', diag_kind='kde', palette='Set2')
plt.savefig('pairplot.png', dpi=150)
plt.show()

# 3.3 Correlation heatmap
plt.figure(figsize=(8, 6))
corr = df[numeric_cols].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Matrix')
plt.tight_layout()
plt.savefig('correlation_heatmap.png', dpi=150)
plt.show()

# 3.4 Boxplots of ED by categorical features
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for i, cat_col in enumerate(categorical_cols[:4]):  # limit to 4 for space
    ax = axes[i//2, i%2]
    sns.boxplot(x=cat_col, y='ED', data=df, ax=ax)
    ax.set_title(f'ED vs {cat_col}')
    ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig('boxplots_ED.png', dpi=150)
plt.show()

# ============================================================
# 4. CLUSTERING
# ============================================================
print("\n" + "="*50)
print("CLUSTERING ANALYSIS")
print("="*50)

# 4.1 Scale numeric features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[numeric_cols])

# 4.2 Determine optimal number of clusters using Elbow method
inertias = []
K_range = range(2, 11)
for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    inertias.append(kmeans.inertia_)

plt.figure(figsize=(8, 5))
plt.plot(K_range, inertias, 'bo-')
plt.xlabel('Number of clusters (k)')
plt.ylabel('Inertia')
plt.title('Elbow Method for Optimal k')
plt.grid(True)
plt.savefig('elbow.png', dpi=150)
plt.show()

# Choose k=3 (or based on elbow, let's use 3)
k = 3
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
df['Cluster'] = kmeans.fit_predict(X_scaled)

# 4.3 Visualize clusters with PCA
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
df['PCA1'] = X_pca[:, 0]
df['PCA2'] = X_pca[:, 1]

plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='PCA1', y='PCA2', hue='Cluster', palette='viridis', alpha=0.7)
plt.title('PCA Projection of Clusters')
plt.savefig('clusters_pca.png', dpi=150)
plt.show()

# 4.4 Cluster profiles
print("\nCluster sizes:")
print(df['Cluster'].value_counts().sort_index())

print("\nCluster centroids (scaled):")
centroids = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_), columns=numeric_cols)
print(centroids)

print("\nCluster profiles - average numeric features:")
cluster_means = df.groupby('Cluster')[numeric_cols].mean()
print(cluster_means.round(2))

print("\nCluster distribution of categorical features:")
for col in categorical_cols:
    print(f"\n{col} by cluster:")
    cross_tab = pd.crosstab(df['Cluster'], df[col], normalize='index')
    print(cross_tab.round(2))

# 4.5 Additional: Clusters with SafetyLabel distribution
print("\nSafetyLabel distribution per cluster:")
safety_cross = pd.crosstab(df['Cluster'], df['SafetyLabel'], normalize='index')
print(safety_cross.round(2))

# ============================================================
# 5. SAVE CLUSTERED DATA (optional)
# ============================================================
df.to_csv(r"D:\ED\LGBM\45_clustered.csv", index=False)
print("\nClustered dataset saved to 45_clustered.csv")