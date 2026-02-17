# 1. Import required libraries
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import pandas as pd

# 2. Load dataset
iris = load_iris()
data = pd.DataFrame(iris.data, columns=iris.feature_names)
data['target'] = iris.target

# 3. Split data
X = data.drop('target', axis=1)
y = data['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Initialize and train model
model = LogisticRegression(max_iter=200)  # This defines 'model'
model.fit(X_train, y_train)

# 5. Now you can use model.predict()
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Accuracy:", accuracy)
import matplotlib.pyplot as plt

# Get feature importance (coefficients)
importance = model.coef_[0]
features = iris.feature_names

plt.barh(features, importance)
plt.title("Feature Importance in Iris Classification")
plt.show()