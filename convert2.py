import pickle
import sys

print("Loading model...", flush=True)
try:
    with open('gesture_model.pkl', 'rb') as f:
        m = pickle.load(f)
    print(f"Model loaded: {type(m)}", flush=True)
    print(f"Classes: {m.classes_}", flush=True)
    print(f"N features: {m.n_features_in_}", flush=True)
except Exception as e:
    print(f"Load error: {e}", flush=True)
    sys.exit(1)

print("Converting...", flush=True)
try:
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    initial_type = [('float_input', FloatTensorType([None, m.n_features_in_]))]
    onx = convert_sklearn(m, initial_types=initial_type)
    print("Conversion done", flush=True)
except Exception as e:
    print(f"Conversion error: {e}", flush=True)
    sys.exit(1)

print("Saving...", flush=True)
try:
    with open('gesture_model.onnx', 'wb') as f:
        f.write(onx.SerializeToString())
    print("SAVED OK!", flush=True)
except Exception as e:
    print(f"Save error: {e}", flush=True)