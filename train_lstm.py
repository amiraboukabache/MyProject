import numpy as np
import os
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

sequences_path = "sequences"
X = []
y = []

for gesture in os.listdir(sequences_path):
    gesture_path = os.path.join(sequences_path, gesture)
    if not os.path.isdir(gesture_path):
        continue
    for seq_file in os.listdir(gesture_path):
        seq = np.load(os.path.join(gesture_path, seq_file))
        X.append(seq)
        y.append(gesture)

X = np.array(X)
y = np.array(y)

# Data augmentation - create more sequences
def augment(seq):
    noise = seq + np.random.normal(0, 0.01, seq.shape)
    scaled = seq * np.random.uniform(0.9, 1.1)
    shifted = seq + np.random.uniform(-0.05, 0.05)
    return [noise, scaled, shifted]

X_aug = []
y_aug = []
for i in range(len(X)):
    X_aug.append(X[i])
    y_aug.append(y[i])
    for aug in augment(X[i]):
        X_aug.append(aug)
        y_aug.append(y[i])

X_aug = np.array(X_aug)
y_aug = np.array(y_aug)

le = LabelEncoder()
y_encoded = le.fit_transform(y_aug)
y_cat = to_categorical(y_encoded)

X_train, X_test, y_train, y_test = train_test_split(X_aug, y_cat, test_size=0.2, random_state=42)

model = Sequential([
    LSTM(128, return_sequences=True, input_shape=(30, 195)),
    Dropout(0.3),
    LSTM(64),
    Dropout(0.3),
    Dense(64, activation='relu'),
    Dense(len(le.classes_), activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

early_stop = EarlyStopping(monitor='val_accuracy', patience=10, restore_best_weights=True)

model.fit(X_train, y_train, epochs=100, batch_size=16,
          validation_data=(X_test, y_test), callbacks=[early_stop])

loss, accuracy = model.evaluate(X_test, y_test)
print(f"\nTest accuracy: {accuracy*100:.2f}%")

model.save("gesture_lstm.h5")
with open("lstm_labels.pkl", "wb") as f:
    pickle.dump(le, f)

print("Model saved as gesture_lstm.h5")