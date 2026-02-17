import streamlit as st
import json
import cv2
import numpy as np
from PIL import Image

# Function to overlay polygons on the image
def overlay_annotations(image, shapes):
    for shape in shapes:
        if shape['shape_type'] == 'polygon':
            points = np.array(shape['points'], dtype=np.int32)
            # Reshape to make it compatible with OpenCV polygon function
            points = points.reshape((-1, 1, 2))
            # Define color (using a random color for each label)
            color = (0, 255, 0)  # Green color for this example
            cv2.polylines(image, [points], isClosed=True, color=color, thickness=2)
            
            # Optionally add label text for each polygon
            label = shape['label']
            cv2.putText(image, label, tuple(points[0][0]), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    return image

# Streamlit app
def main():
    st.title("Polygon Annotation Viewer")

    # Upload JSON file
    uploaded_json = st.file_uploader("Upload JSON file with annotations", type=["json"])

    # Upload image file
    uploaded_image = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

    if uploaded_json and uploaded_image:
        try:
            # Load the JSON data
            json_data = json.load(uploaded_json)

            # Check if 'shapes' key exists and handle case if not
            if 'shapes' in json_data:
                shapes = json_data['shapes']
            else:
                st.error("No 'shapes' found in the JSON file.")
                return

            # Read image
            image = Image.open(uploaded_image)
            image = np.array(image)

            # Convert image from RGB to BGR (OpenCV format)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            # Overlay polygons on the image
            annotated_image = overlay_annotations(image, shapes)

            # Convert annotated image back to RGB for Streamlit display
            annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
            
            # Use the updated parameter 'use_container_width'
            st.image(annotated_image, caption='Annotated Image', use_container_width=True)

            # Optionally save annotated image
            if st.button('Save Annotated Image'):
                save_path = 'annotated_image.jpg'
                cv2.imwrite(save_path, cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
                st.success(f"Image saved as {save_path}")

        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON: {e}")
            return

if __name__ == "__main__":
    main()
