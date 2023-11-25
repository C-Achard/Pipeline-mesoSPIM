import streamlit as st


def main():
    st.title("DataJoint pipeline for brain registration and segmentation")

    col1, col2 = st.columns([1, 1])

    col1.header("Parameters for brain registration")
    param1 = col1.number_input("Enter N:", min_value=0, step=1, format="%d")
    values = []
    if param1 > 0:
        for i in range(param1):
            user_input = col1.text_input(f"Enter value {i + 1}:", key=i)
            values.append(user_input)

    param2 = col1.text_input("Parameter 2", "")
    param3 = col1.selectbox(
        "Parameter 3", ["Option A", "Option B", "Option C"]
    )

    col2.header("Parameters for ")
    param4 = col2.checkbox("Parameter 4", value=False)
    param5 = col2.slider("Parameter 5", min_value=0, max_value=100, value=50)
    param6 = col2.radio("Parameter 6", ["Choice X", "Choice Y", "Choice Z"])


if __name__ == "__main__":
    main()
