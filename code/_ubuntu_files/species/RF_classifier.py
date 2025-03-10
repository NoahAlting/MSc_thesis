import os
import laspy
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def extract_features_from_las(las_file_path):
    """
    Load a LAS file using laspy and extract some basic features.
    For now, we compute:
      - Number of points in the tree pointcloud
      - Average intensity (if available)
    
    You can extend this function to include additional features such as:
      - Sphericity, linearity
      - Leaf-area-index
      - Height-based percentiles (e.g., features at 100/75/50/20% of the total tree height)
    """
    try:
        las = laspy.read(las_file_path)
    except Exception as e:
        print(f"Error reading {las_file_path}: {e}")
        return None

    num_points = len(las.points)
    # Check if intensity data is available in the LAS file.
    if 'intensity' in las.point_format.dimension_names:
        mean_intensity = np.mean(las.intensity)
    else:
        mean_intensity = np.nan

    features = {
        'num_points': num_points,
        'mean_intensity': mean_intensity
    }
    return features

def load_features_from_folder(folder_path):
    """
    Process all LAS files in the provided folder.
    Assumes that each file name contains the tree_id (e.g., "tree_123.las").
    Returns a DataFrame with the extracted features for each tree.
    """
    feature_list = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.las'):
            # Extract tree_id from filename
            tree_id = int(os.path.splitext(filename)[0].split('_')[-1])
            file_path = os.path.join(folder_path, filename)
            features = extract_features_from_las(file_path)
            if features is not None:
                features['tree_id'] = tree_id
                feature_list.append(features)
    
    features_df = pd.DataFrame(feature_list)
    return features_df

def main():
    # Define file paths 
    csv_path = 'single_matches.csv'
    las_folder_path = '../wrapper/clusters'  

    # Load the CSV file with tree labels and pre-calculated features
    df_labels = pd.read_csv(csv_path)
    
    # Load additional features extracted from LAS files
    df_features = load_features_from_folder(las_folder_path)
    
    # Merge the two data sources on tree_id
    df_merged = pd.merge(df_labels, df_features, on='tree_id', how='inner')
    if df_merged.empty:
        print("Merged dataframe is empty. Check your file paths and tree_id matching.")
        return

    # For demonstration, we will use a subset of available features.
    # Here we use 'match_count' (from CSV), and the LAS-derived features.
    feature_columns = ['match_count', 'num_points', 'mean_intensity']
    # Verify all required columns are available
    missing_cols = [col for col in feature_columns if col not in df_merged.columns]
    if missing_cols:
        print(f"Missing columns in the merged DataFrame: {missing_cols}")
        return

    X = df_merged[feature_columns]
    y = df_merged['species']  # Target label

    # Split into training and testing sets (80/20 split)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Initialize and train the Random Forest classifier
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)

    # Make predictions on the test set
    y_pred = rf.predict(X_test)

    # Evaluate the classifier
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("Accuracy Score:", accuracy_score(y_test, y_pred))

if __name__ == "__main__":
    main()
