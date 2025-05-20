import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv("species_counts_H1.csv")

# Column names
species_col = df.columns[0]
count_col = df.columns[1]

# Filter to species with at least 50 samples
df_filtered = df[df[count_col] >= 50].sort_values(by=count_col, ascending=False)

# remove the top 1
df_filtered = df_filtered.iloc[1:]

# Plot vertically
plt.figure(figsize=(max(12, len(df_filtered) * 0.4), 6))
sns.barplot(x=df_filtered[species_col],
            y=df_filtered[count_col],
            palette="crest")

plt.xticks(rotation=45, ha='right')  # angled labels
plt.xlabel("Species (≥50 samples)")
plt.ylabel("Count")
plt.title(f"Species with ≥50 Labeled Trees (n={len(df_filtered)}) excluding 'nader te bepalen'")
plt.grid(True, axis='y')
plt.tight_layout()

# Show or save
plt.show()
# plt.savefig("species_barplot_50plus_angled.png")
