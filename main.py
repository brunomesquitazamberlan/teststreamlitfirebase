import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import warnings
from functools import partial
import json
import firebase_admin
import numpy as np
warnings.filterwarnings('ignore')


firebase_credentials = dict(st.secrets["firebase"]['my_project_settings'])

#################################################################
# Verifique se já existe um app inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()
################################################################

def get_document_by_specific_parameter(collection_name: str,
                                       field: str,
                                       field_value: str) -> dict:

    collection = db.collection(collection_name)
    
    documents_list = collection.where(field, '==', field_value).stream()
    
    results = [document.to_dict() for document in documents_list]
    
    return results[0]

get_field_list = lambda collection_name, field, field_value, parameter_name: get_document_by_specific_parameter(collection_name, field, field_value)[parameter_name]

get_documents_ids_by_specific_user = lambda collection_name, user_name: [document.id for document in db.collection(collection_name).where("usuario", '==', user_name).stream()]
get_documents_ids_by_specific_user_period = lambda collection_name, user_name, period: [document.id for document in db.collection(collection_name).where("usuario", '==', user_name).where("periodo", '==', period).stream()]
generate_filtered_dataframe_by_period = lambda pandas_dataframe, period_column, period: pandas_dataframe[pandas_dataframe[period_column] == period]


def convert_datetime_into_period_string(input_datetime: datetime):
    
    period_string = f"{input_datetime.year}-{input_datetime.month}"

    return period_string

def format_firebase_datetime_format(input_datetime: datetime):

    try:
        formatted_date_time = f"{input_datetime.day}/{input_datetime.hour}/{input_datetime.year}"
        return formatted_date_time
    except:
        return input_datetime

get_list_of_unique_index = lambda collection_name, field: list(set([document.to_dict()[field] for document in db.collection(collection_name).stream() if field in document.to_dict()])) 



def return_field_values_by_key(collection_name, field, value, key):

    data_structure = {document.id: document.to_dict()
        for document in db.collection(collection_name).stream()}
    
    result_list = [
        document.get(key) for id, document in data_structure.items() if document.get(field) == value
    ]


    return result_list 


def generate_dataframe_by_firebase_collection_filtered_by_user(collection_name: str,
                                   list_of_attributes: list,
                                   user: str):
    
    
    get_list_attribute = partial(return_field_values_by_key, collection_name,
                                 "usuario",
                                 user)
    
    list_of_lists = [get_list_attribute(attrib) for attrib in list_of_attributes]

    max_list_lenght = max([len(attrib) for attrib in list_of_lists])

    adjusted_data_structure = {attrib: get_list_attribute(attrib) + 
                               [None for _ in range(max_list_lenght-len(get_list_attribute(attrib)))]
                               for attrib in list_of_attributes}
    
    pandas_dataframe = pd.DataFrame(adjusted_data_structure, index=get_documents_ids_by_specific_user(collection_name, user))

    return pandas_dataframe

def updated_generate_dataframe_by_firebase_collection_filtered_by_user(collection_name: str,
                                   list_of_attributes: list,
                                   user: str):
    
    
    get_list_attribute = partial(return_field_values_by_key, collection_name,
                                 "usuario",
                                 user)
    
    list_of_lists = [get_list_attribute(attrib) for attrib in list_of_attributes]

    max_list_lenght = max([len(attrib) for attrib in list_of_lists])

    adjusted_data_structure = {attrib: get_list_attribute(attrib) + 
                               [None for _ in range(max_list_lenght-len(get_list_attribute(attrib)))]
                               for attrib in list_of_attributes}
    
    pandas_dataframe = pd.DataFrame(adjusted_data_structure)

    return pandas_dataframe

def transform_dataframe_columns(input_dataframe: pd.DataFrame,
                                column: str,
                                function_to_apply):
    input_dataframe[column] = [function_to_apply(element) for element in input_dataframe[column].to_list()]

    return input_dataframe

def create_document(collection_name: str, item: dict):
    
    collection_ref = db.collection(collection_name)

    try:
        doc_ref = collection_ref.add(item)
        return True
    
    except:
        return False
    
def update_document_by_id(collection_name, doc_id, updated_data):
    try:

        # Referência para o documento específico na coleção
        doc_ref = db.collection(collection_name).document(doc_id)

        # Atualiza os campos do documento com os dados passados
        doc_ref.set(updated_data)

        return True

    except:
        return False

def delete_doc_by_id(collection_name: str, doc_id: str):
    try:
        db.collection(collection_name).document(doc_id).delete()
        return True
    except:
        return False


def return_dataframe_adjustments_and_removed_itens(df_original: pd.DataFrame,
                                                   df_adjusted: pd.DataFrame) -> list:
    df_original_dict = df_original.to_dict('index')
    df_adjusted_dict = df_adjusted.to_dict('index')
    
    def removed_itens(df_original: pd.DataFrame, df_adjusted: pd.DataFrame) -> list:
        return [index for index in list(df_original.index) if index not in list(df_adjusted.index)]
    
    def return_dict_data_adjustments(dict_original:dict,
                                 dict_adjusted: dict ) -> dict:
    
        ids_to_check = [key for key, value in dict_adjusted.items()] 
    
        list_to_return = {id: dict_adjusted.get(id) for id in ids_to_check if dict_original.get(id) != dict_adjusted.get(id)}  

        return list_to_return if list_to_return != [{}] else None
    
    return [return_dict_data_adjustments(df_original_dict, df_adjusted_dict),removed_itens(df_original, df_adjusted)]
    



update_documents_from_adjusted_return = lambda adjusted_dataframe_return: [update_document_by_id("registros", key, value) for key, value in adjusted_dataframe_return.items()]
remove_documents_from_adjusted_return = lambda documents_list: [delete_doc_by_id("registros", doc) for doc in documents_list]

    
def main():

    # Sidebar para seleção de operações
    operation = st.sidebar.selectbox("Selecione a operação desejada", ["Lançar horas", "Visualizar/Alterar Lançamentos"],
                                     placeholder="Selecione uma operação",
                                     index=None)

    match operation:
        case "Lançar horas":
            lancar_horas()
        case "Visualizar/Alterar Lançamentos":
            visualizar_alterar_horas()
        case _:
            tela_inicial()

def tela_inicial():
    st.header("Lance e acompanhe os seus lançamentos de horas!")

def lancar_horas():
    
    st.title("Lançamento de Horas")
        
    with st.spinner("Em progresso"):

        if "usuario_selecionado" not in st.session_state:
            st.session_state["usuario_selecionado"] = ""
        if "cliente" not in st.session_state:
            st.session_state["cliente"] = ""
        
    
        st.session_state["usuario_selecionado"] = st.selectbox("Selecione o usuário:", get_list_of_unique_index("usuarios", "nome"), placeholder="Selecione o usuário",
                                     index=None)
        st.session_state["cliente"] = st.selectbox("Selecione o cliente:", get_list_of_unique_index("taxonomia", "cliente"), placeholder="Selecione o cliente",
                                     index=None)
        
    
    if st.session_state["cliente"]:

        
    
        with st.form("Fazer lançamento de hora",
                     clear_on_submit=True):


            st.write("Adicionar Novo Registro")
            col1, col2 = st.columns(2)
            with col1:
                nova_data = st.date_input("Data")
                projetos_atividades = get_field_list("taxonomia", "cliente", st.session_state["cliente"], "projetos_atividades")
                novo_projeto_atividade = st.selectbox("Projetos / Atividades", projetos_atividades, key="projetos_atividades", placeholder="", index=None)
                novo_comentario = st.text_area("Comentário")

            with col2:
                nova_quantidade_horas = st.number_input("Quantidade de Horas", min_value=0.0, max_value=24.0, step=0.5)
                tipo = get_field_list("taxonomia", "cliente", st.session_state["cliente"], "detalhe")
                nova_classificacao = st.selectbox("Classificação", tipo, key="classificacao", placeholder="", index=None)
                
                
            submitted = st.form_submit_button("Adicionar Registro")

            if submitted:
                register = {
                    'cliente': st.session_state["cliente"],
                    'detalhe': nova_classificacao,
                    'periodo': convert_datetime_into_period_string(nova_data),
                    'qtde_horas': nova_quantidade_horas,
                    'usuario': st.session_state["usuario_selecionado"],
                    'data': f"{nova_data.year}-{nova_data.month}-{nova_data.day}",
                    'comentario': novo_comentario
                }
                
                # Exibe o botão para limpar os campos após a inclusão
                create_document("registros", register)
                st.warning("Registro incluído com sucesso")           

    

def visualizar_alterar_horas():
    st.title("Visualizar/Alterar Lançamentos de Horas")
    
    with st.spinner("Em progresso"):
    
        usuario_selecionado = st.selectbox("Selecione o usuário:", get_list_of_unique_index("registros", "usuario"), placeholder="Selecione o usuário",
                                 index=None)
    
        with st.spinner("Em progresso"):
            periodo_selecionado = st.selectbox("Selecione o período:", set(return_field_values_by_key("registros", "usuario", usuario_selecionado, "periodo")), placeholder="Selecione o período",
                                     index=None) 

    if usuario_selecionado and periodo_selecionado:

        with st.spinner("Em progresso"):

            st.session_state["pandas_dataframe_usuario_periodo"] = generate_filtered_dataframe_by_period(
                generate_dataframe_by_firebase_collection_filtered_by_user(
                "registros", 
                ["cliente", "comentario", "data", "periodo", "qtde_horas"],
                usuario_selecionado), "periodo", periodo_selecionado)
            

            total_horas = st.session_state["pandas_dataframe_usuario_periodo"]["qtde_horas"].sum()
            st.markdown(f"<h3 style='text-align: left; color: #4169E1;'>Total: {total_horas:.1f} horas</h3>", unsafe_allow_html=True)
            

            edited_df = st.data_editor(st.session_state["pandas_dataframe_usuario_periodo"], num_rows="dynamic", hide_index=True)
        
            if not edited_df.equals(st.session_state["pandas_dataframe_usuario_periodo"]):
                
                updated = return_dataframe_adjustments_and_removed_itens(st.session_state["pandas_dataframe_usuario_periodo"],
                                      edited_df)
                
                updated_with_usuario = {key: {**value, 'usuario': usuario_selecionado} for key, value in updated[0].items()}
                removed_documents = updated[1]


                update_documents_from_adjusted_return(updated_with_usuario)

                if removed_documents != []:
                    remove_documents_from_adjusted_return(removed_documents)

def cadastrar_usuarios():

    st.title("Cadastro de usuários")



    with st.spinner("Em progresso"):

        with st.form("Fazer cadastro de usuário",
                     clear_on_submit=True):
            st.write("Adicionar Usuário")
            
            novo_nome = st.text_input("Nome")
            
            time = get_list_of_unique_index("usuarios", "time")
            novo_time = st.selectbox("Time", time, key="time", placeholder="", index=None)

            submitted = st.form_submit_button("Adicionar Usuário")
            
            if submitted:
                register = {
                    'nome': novo_nome,
                    'time': novo_time,
                    'usuario': 'admin'
                }
                
                # Exibe o botão para limpar os campos após a inclusão
                create_document("usuarios", register)
                st.warning("Registro incluído com sucesso")

                with st.spinner("Em progresso"):
                    st.session_state["pandas_dataframe_tabela_usuarios"] = generate_dataframe_by_firebase_collection_filtered_by_user("usuarios", ["nome", "time"],"admin")
                    st.markdown(f"<h3 style='text-align: left; color: #4169E1;'>Apenas Visualização! Funcionalidade de edição em Construção</h3>", unsafe_allow_html=True)
                    edited_df_usuarios = st.data_editor(st.session_state["pandas_dataframe_tabela_usuarios"], num_rows="dynamic", hide_index=True)

                    if not edited_df_usuarios.equals(st.session_state["pandas_dataframe_tabela_usuarios"]):
                
                        updated = return_dataframe_adjustments_and_removed_itens(st.session_state["pandas_dataframe_usuario_periodo"],
                                      edited_df_usuarios)
                
                        updated_with_usuario = {key: {**value, 'usuario': 'admin'} for key, value in updated[0].items()}
                        removed_documents = updated[1]


                        update_documents_from_adjusted_return(updated_with_usuario)

                        if removed_documents != []:
                            remove_documents_from_adjusted_return(removed_documents)




        #st.session_state["pandas_dataframe_tabela_usuarios"] = updated_generate_dataframe_by_firebase_collection_filtered_by_user("usuarios", ["nome", "time"],"admin")

        #edited_df_usuarios = st.data_editor(st.session_state["pandas_dataframe_tabela_usuarios"], num_rows="dynamic", hide_index=True)


if __name__ == "__main__":
    main()


