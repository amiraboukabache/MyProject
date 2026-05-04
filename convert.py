import pickle
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

print("Loading model...")
with open('gesture_model.pkl', 'rb') as f:
    model = pickle.load(f)

print(f"Model type: {type(model)}")

print("Converting to ONNX...")
initial_type = [('float_input', FloatTensorType([None, 63]))]
onx = convert_sklearn(model, initial_types=initial_type)

with open('gesture_model.onnx', 'wb') as f:
    f.write(onx.SerializeToString())

print("Done! gesture_model.onnx created successfully")