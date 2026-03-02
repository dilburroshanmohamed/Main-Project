import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import os

# Get project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def train_model():

    # Load dataset
    dataset_path = os.path.join(BASE_DIR, "employee_stress_dataset_2000.csv")
    df = pd.read_csv(dataset_path)

    print("Dataset loaded successfully!")

    # Drop missing values
    df = df.dropna()

    # Select features
    X = df[['Work_Hours_per_Week',
            'Workload_Score',
            'Job_Satisfaction',
            'Sleep_Hours',
            'Physical_Activity_Hrs',
            'Caffeine_Intake',
            'Stress_Level']]

    y = df['Mental_Health_Score']

    # Scaling
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # Model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    print("Model trained successfully!")

    # Save model
    joblib.dump(model, os.path.join(BASE_DIR, "stress_model.pkl"))
    joblib.dump(scaler, os.path.join(BASE_DIR, "scaler.pkl"))

    print("Model and scaler saved successfully!")

if __name__ == "__main__":
    train_model()