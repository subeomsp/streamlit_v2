import streamlit as st 
# from streamlit_extras.dataframe_explorer import dataframe_explorer
from streamlit_option_menu import option_menu
import re
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, ColumnsAutoSizeMode
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import json

review_df = pd.read_pickle('/Users/subeomlee/Desktop/서강머/streamlit/coupang_clean_v4.pkl')
review_df.loc[:, 'month'] = review_df['일자'].apply(lambda x: x[:7])

if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

# Create an empty container
placeholder = st.empty()

actual_email = "admin"
actual_password = "123456"

if st.session_state.login_status == False:
    # Insert a form in the container
    with placeholder.form("login"):
        st.markdown("로그인 정보를 입력해주세요")
        email = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인")

    if submit and email == actual_email and password == actual_password:
        # If the form is submitted and the email and password are correct,
        # clear the form/container and display a success message
        st.session_state.login_status = True
        placeholder.empty()
    elif submit and email != actual_email and password != actual_password:
        st.error("Login failed")
    else:
        pass

if st.session_state.login_status == True:
    with st.sidebar:
        choose = option_menu("메뉴", ['지수설명', '업체관리', '분석알고리즘', '주요 서비스 분야/영역', '상담문의'],
                            menu_icon="app-indicator", default_index=0,
                            key = 'choosen_option',
                            styles={
            "container": {"padding": "5!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "25px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#02ab21"},
            }
        )

    if st.session_state.choosen_option == '업체관리':
        st.header('업체관리')
        st.divider()
    
        with st.form("input_form"):
            form_col1, form_col2, form_col3, form_col4 = st.columns([2,2,2,2])
            with form_col1:
                category = review_df['카테고리'].unique().tolist()
                st.selectbox(
                    '상품구분',
                    tuple(category),
                    key = 'category_selected'
                )
            
            with form_col2:
                st.selectbox(
                    '지수 구분',
                    ('신선', '맛', '양', '가격', '배송', '포장'),
                    key = 'index_selected'
                )
            
            with form_col3:
                selected_seller = review_df.query('카테고리 == "%s"' % st.session_state.category_selected)['셀러'].unique().tolist()
                st.selectbox(
                    '업체 구분',
                    tuple(selected_seller),
                    key = 'seller_selected'
                )
            # with form_col4:
            #     selected_date = sorted(review_df['month'].unique().tolist())
            #     st.selectbox(
            #         '일자 선택',
            #         tuple(selected_date),
            #         key = 'date_selected'
            #     )
            with form_col4:
                st.write("")
                submitted = st.form_submit_button('조회')
                if 'submitted' not in st.session_state:
                    st.session_state['submitted'] = False

                if submitted:
                    st.session_state.submitted = True
            
        if st.session_state['submitted'] == True:
            target_df = review_df[(review_df['셀러'] == st.session_state.seller_selected)&(review_df['카테고리'] == st.session_state.category_selected)]

            if target_df.empty:
                st.write('조회된 데이터가 존재하지 않습니다')
            else:
                product_list = target_df['제품명'].unique().tolist()
                keyword_list = ['신선', '맛', '양', '가격', '배송', '포장']

                def get_keyword_value(x):
                    keyword_vals  = []
                    for keyword in keyword_list:
                        vals = x[keyword].value_counts()
                        good_val = vals.get(1)
                        if good_val == None:
                            good_val = 0
                        bad_val = vals.get(-1)
                        if bad_val == None:
                            bad_val = 0
                        try:
                            final_val = int(round(good_val / (good_val + bad_val),2) * 100)
                        except:
                            final_val = 0
                        
                        keyword_vals.append(final_val)
                    return keyword_vals
                target_by_month = target_df.groupby(['제품명', 'month']).apply(lambda x: get_keyword_value(x)).rename('values').reset_index()
                for idx, keyword in enumerate(keyword_list):
                    target_by_month.loc[:, keyword] = target_by_month['values'].apply(lambda x: x[idx])
                
                st.radio(
                        "지수 선택",
                        tuple(keyword_list),
                        key = 'keyword_selected',
                        horizontal=True
                    )

                down_col1, down_col2 = st.columns([2,2])    
                
                with down_col1:

                    recent_df = target_by_month.sort_values(['제품명', 'month'], ascending=[True, False]).groupby('제품명').head(1)
                    recent_df = recent_df.sort_values(st.session_state.keyword_selected, ascending=True)
                    fig = px.bar(recent_df,
                                x = st.session_state.keyword_selected, y = '제품명')

                    st.plotly_chart(fig, use_container_width=True)
                with down_col2:
                    recent_df_to_show = recent_df[['제품명'] + keyword_list]
                    recent_df_to_show = recent_df_to_show.sort_values(st.session_state.keyword_selected, ascending=False)
                    go = GridOptionsBuilder.from_dataframe(recent_df_to_show)
                    go.configure_default_column(min_column_width=1)
                    go.configure_pagination(enabled=True, paginationPageSize = 10, paginationAutoPageSize=False)
                    go.configure_selection(selection_mode='single', use_checkbox=True)
                    recent_df_to_show_gb = go.build()
                    recent_df_to_show_df = AgGrid(recent_df_to_show, recent_df_to_show_gb,
                            fit_columns_on_grid_load=True)

                    if 'row_selected' not in st.session_state:
                        st.session_state['row_selected'] = False
                    recent_data_selected = recent_df_to_show_df['selected_rows']
                    if recent_data_selected:
                        st.session_state['row_selected'] = True
    
                if st.session_state['row_selected'] == True:
                    st.divider()
                    if 'selected_product' not in st.session_state:
                        st.session_state['selected_product'] = None
                    st.session_state.selected_product = [row['제품명'] for row in recent_data_selected][0]
                    # st.write(target_by_month)
                    selected_product_by_month = target_by_month[target_by_month['제품명'] == st.session_state.selected_product]
                    selected_product_fig_df = selected_product_by_month[['month', '신선', '맛', '양', '가격', '배송', '포장']]
                    selected_product_fig_df = selected_product_fig_df.rename(columns={'month' : '월'})
                    selected_product_fig_df = selected_product_fig_df.melt(id_vars='월', var_name='지수', value_name='점수')
                    selected_product_fig = px.bar(
                        selected_product_fig_df,
                        x = '월',
                        y = '점수',
                        color = '지수',
                        barmode='group',
                        title=st.session_state.selected_product
                    )
                    # st.write(selected_product_by_month)
                    st.plotly_chart(selected_product_fig, use_container_width=True)
                    # st.write(recent_data_selected)

                    # st.dataframe(recent_df_to_show, use_container_width=True)
