import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re  # <--- 这里补上了缺失的导入

# ================= 1. Configuration & Styling =================
# Set style to white (no grid)
sns.set_style("white")
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

INPUT_PATH = "/Users/cyz/cheche/Cross-border e-commerce analysis/iphone_cases_analysis_final.csv"
OUTPUT_DIR = "/Users/cyz/cheche/Cross-border e-commerce analysis"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "iphone17_relevant_only_clean.csv")
PLOT_DIR = os.path.join(OUTPUT_DIR, "plots_clean")

os.makedirs(PLOT_DIR, exist_ok=True)

print("🚀 Starting Data Analysis & Cleaning Task...")

# ================= 2. Data Loading =================
try:
    df = pd.read_csv(INPUT_PATH)
except FileNotFoundError:
    print(f"❌ Error: File not found at {INPUT_PATH}")
    exit()

# Ensure necessary columns exist
required_columns = ['Title', 'Price', 'Rating', 'Reviews', 'Brand']
if not all(col in df.columns for col in required_columns):
    print(f"❌ Error: CSV must contain columns: {required_columns}")
    exit()

# ================= 3. Data Cleaning =================
# 1. Clean Price: Remove currency symbols and convert to float
def clean_price(price):
    if pd.isna(price):
        return np.nan
    # Use regex to find the first number (handling decimals)
    match = re.search(r'[\d,]+\.?\d*', str(price))
    if match:
        return float(match.group().replace(',', ''))
    return np.nan

df['Price_Clean'] = df['Price'].apply(clean_price)

# 2. Filter for iPhone 17 (Case Insensitive)
# We look for "iPhone 17" specifically to avoid matching "iPhone 17 Pro Max" if needed,
# but usually, we want all variants.
df['Title_Lower'] = df['Title'].str.lower()
df_iphone17 = df[df['Title_Lower'].str.contains(r'iphone\s*17', regex=True)].copy()

# 3. Drop rows with missing Price (The fix you requested)
initial_count = len(df_iphone17)
df_iphone17.dropna(subset=['Price_Clean'], inplace=True)
dropped_count = initial_count - len(df_iphone17)

print(f"🔍 Found {initial_count} items related to iPhone 17.")
if dropped_count > 0:
    print(f"🧹 Dropped {dropped_count} items due to missing Price data.")

# Save the cleaned CSV
df_iphone17.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Saved filtered data to: {OUTPUT_CSV}")

# ================= 4. Statistical Analysis & Visualization =================

# Analysis 1: Price Distribution (Histogram)
plt.figure(figsize=(10, 6))
sns.histplot(df_iphone17['Price_Clean'], bins=10, color='#4c72b0', kde=True)
plt.title('Price Distribution: iPhone 17 Cases', fontsize=14)
plt.xlabel('Price (SGD)', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, '1_price_distribution.png'))
plt.close()

# Analysis 2: Rating vs Reviews (Scatter Plot)
# Ensure Reviews is numeric
df_iphone17['Reviews_Clean'] = pd.to_numeric(df_iphone17['Reviews'], errors='coerce')

plt.figure(figsize=(10, 6))
sns.scatterplot(data=df_iphone17, x='Reviews_Clean', y='Rating', size='Price_Clean', hue='Price_Clean', palette='viridis', alpha=0.7)
plt.title('Rating vs. Number of Reviews (Size indicates Price)', fontsize=14)
plt.xlabel('Number of Reviews', fontsize=12)
plt.ylabel('Rating (Stars)', fontsize=12)
plt.legend(title='Price', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, '2_rating_vs_reviews.png'))
plt.close()

# Analysis 3: Brand Count (Bar Chart)
plt.figure(figsize=(10, 6))
# Get top 10 brands to keep it clean
brand_counts = df_iphone17['Brand'].value_counts().head(10)
sns.barplot(x=brand_counts.index, y=brand_counts.values, palette='Blues_d')
plt.title('Top 10 Brands for iPhone 17 Cases', fontsize=14)
plt.xlabel('Brand', fontsize=12)
plt.ylabel('Number of Products', fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, '3_top_brands.png'))
plt.close()

# Analysis 4: Price by Brand (Box Plot - Top 5 Brands)
top_5_brands = df_iphone17['Brand'].value_counts().head(5).index
df_top5_brands = df_iphone17[df_iphone17['Brand'].isin(top_5_brands)]

plt.figure(figsize=(10, 6))
sns.boxplot(data=df_top5_brands, x='Brand', y='Price_Clean', palette='Set2')
plt.title('Price Variance by Top 5 Brands', fontsize=14)
plt.xlabel('Brand', fontsize=12)
plt.ylabel('Price (SGD)', fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, '4_price_by_brand.png'))
plt.close()

print("✅ Analysis and Visualization completed successfully.")
print(f"📊 Plots saved in: {PLOT_DIR}")