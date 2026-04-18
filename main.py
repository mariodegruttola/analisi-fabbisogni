from io import BytesIO
import streamlit as st
import pandas as pd
import datetime as dt

def multi_raw_materials_requirements(df: pd.DataFrame, df_boms: pd.DataFrame):
    single_req = []
    single_info = []
    for _, row in df.iterrows():
        item_code = row["Item"]
        meter = row["Meters"]
        df_raw_material = df_boms[df_boms["Item"] == item_code]
        df_raw_material["Requirement"] = round(df_raw_material["Quantity"] * meter, 3)
        single_req.append(df_raw_material)
        single_info.append({"item_code": item_code, "item_description": df_raw_material.iloc[0]['Item Description'], "meters": meter})

    df_all_raw_material = pd.concat(single_req, axis=0)
    df_all_raw_material.drop(["Quantity"], axis=1, inplace=True)
    df_all_raw_material_grouped = df_all_raw_material.groupby(["Raw Material", "Raw Material Description", "UM"]).sum()

    return single_info, single_req, df_all_raw_material_grouped

def create_xlsx(single_info: dict, single_req: list[pd.DataFrame], df_all_raw_material_grouped: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all_raw_material_grouped.reset_index().to_excel(writer, sheet_name='Totals', index=False)
        
        count = 0
        for df in single_req:
            sr = pd.Series(data=single_info[count])
            df.to_excel(writer, sheet_name=single_info[count]["item_code"], index=False)
            sr.to_excel(writer, startcol=len(df.columns) + 2, startrow=0, sheet_name=single_info[count]["item_code"], header=False)
            count += 1

    output.seek(0)
    return output

def reset_state():
    if "single_info" in st.session_state and "single_req" in st.session_state and "df_all_raw_material_grouped" in st.session_state:
        del st.session_state["single_info"]
        del st.session_state["single_req"]
        del st.session_state["df_all_raw_material_grouped"]

st.set_page_config(
    page_title = "Requirement Analysis",
    page_icon = "",
    layout="wide"
)

st.markdown("""
    <style>
    header { visibility: hidden; }
    .block-container { padding-top: 0rem; }
    </style>
    """, unsafe_allow_html=True)

if "df_boms" not in st.session_state:
    uploaded_file = st.file_uploader("Choose a file", type=["csv"])
    if uploaded_file is not None:
        st.session_state["df_boms"] = pd.read_csv(uploaded_file, sep=';', encoding="ISO-8859-1", skiprows=[1])
        st.rerun()
else:
    df_boms: pd.DataFrame = st.session_state["df_boms"]
    ls_items = df_boms["Item"].unique().tolist()

    if "len_edited_df" not in st.session_state:
        st.session_state["len_edited_df"] = 0

    st.header("Requirement Analysis")
    st.write("Insert items and quantities in the table below")
    col1, col2 = st.columns([0.33, 0.67])
    edited_df = col1.data_editor(
        data=pd.DataFrame(columns=["Item", "Quantity"]),
        column_config={
            "Item": st.column_config.SelectboxColumn(
                width="medium",
                options=ls_items,
                required=True,
            ),
            "Quantity": st.column_config.NumberColumn(
                format="%f",
                min_value=0,
                step=1,
                required=True,
            )
        },
        use_container_width=True,
        num_rows="dynamic",
        on_change=reset_state
    )    

    if col1.button("Analysis"):
        if len(edited_df) > 0:
            st.session_state["single_info"], st.session_state["single_req"], st.session_state["df_all_raw_material_grouped"] = multi_raw_materials_requirements(edited_df, df_boms)
        else: 
            st.toast("The table is empty!")

    if "single_info" in st.session_state and "single_req" in st.session_state and "df_all_raw_material_grouped" in st.session_state:
        tm = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        col1.download_button(
            label="Download Excel file",
            data=create_xlsx(st.session_state["single_info"], st.session_state["single_req"], st.session_state["df_all_raw_material_grouped"]),
            file_name=f"AFT_{tm}.xlsx"
        )

        df_tmp: pd.DataFrame = st.session_state["df_all_raw_material_grouped"]
        df_styled = df_tmp.style.format(precision=3, thousands="", decimal=",")
        col2.dataframe(df_styled, use_container_width=True)

        with st.expander("Single Analysis", expanded=False):
            count = 0
            for df in st.session_state["single_req"]:
                st.header(f":orange[{st.session_state["single_info"][count]["item_code"]}]")
                st.subheader(st.session_state["single_info"][count]["item_description"])
                df_styled = df.style.format(precision=3, thousands="", decimal=",")
                st.dataframe(df_styled, height=(len(df) + 1) * 35 + 3, hide_index=True)
                st.divider()
                count += 1