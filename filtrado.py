import streamlit as st
import pandas as pd
import re

# Configuración
st.set_page_config(page_title="Asistente de Revisión", layout="wide")

# --- INICIALIZACIÓN DEL ESTADO ---
if 'df_final' not in st.session_state:
    st.session_state.df_final = None
if 'eliminados' not in st.session_state:
    st.session_state.eliminados = {
        'duplicados': pd.DataFrame(), 'titulo': pd.DataFrame(),
        'inaccesibles': pd.DataFrame(), 'resumen': pd.DataFrame()
    }

st.title("🎯 Herramienta de Filtrado PRISMA")

# --- BARRA LATERAL: CARGAR PROGRESO O NUEVOS DATOS ---
with st.sidebar:
    st.header("📂 Gestión de Datos")
    
    with st.expander("🆕 Empezar Proyecto Nuevo"):
        wos_files = st.file_uploader("Excels de WoS", accept_multiple_files=True, type=['xls', 'xlsx'])
        others_files = st.file_uploader("CSVs (PubMed/Scopus)", accept_multiple_files=True, type=['csv'])
        if st.button("Procesar y Unificar"):
            lista_total = []
            mapeo = {'Article Title': 'title', 'Title': 'title', 'DOI': 'doi', 'Authors': 'authors', 'Year': 'year', 'Abstract': 'abstract'}
            for f in wos_files:
                df_temp = pd.read_excel(f).rename(columns=mapeo)
                df_temp['fuente'] = f.name
                lista_total.append(df_temp)
            for f in others_files:
                df_temp = pd.read_csv(f).rename(columns=mapeo)
                df_temp['fuente'] = f.name
                lista_total.append(df_temp)
            if lista_total:
                df_unido = pd.concat(lista_total, ignore_index=True)
                df_unido['titulo_limpio'] = df_unido['title'].str.lower().replace(r'[^\w\s]', '', regex=True).str.strip()
                es_duplicado = (df_unido.duplicated(subset=['doi'], keep='first') & df_unido['doi'].notna()) | df_unido.duplicated(subset=['titulo_limpio'], keep='first')
                st.session_state.eliminados['duplicados'] = df_unido[es_duplicado]
                st.session_state.df_final = df_unido[~es_duplicado].copy()
                st.success("¡Unificación completada!")

    st.write("---")
    
    with st.expander("💾 Cargar Progreso Anterior"):
        st.info("Sube aquí los CSVs que descargaste en tu última sesión para continuar.")
        f_unicos = st.file_uploader("Subir 'articulos_finales.csv'", type=['csv'])
        f_tit = st.file_uploader("Subir 'eliminados_titulo.csv'", type=['csv'])
        f_res = st.file_uploader("Subir 'eliminados_resumen.csv'", type=['csv'])
        f_ina = st.file_uploader("Subir 'eliminados_inaccesibles.csv'", type=['csv'])
        
        if st.button("Restaurar Sesión"):
            if f_unicos: st.session_state.df_final = pd.read_csv(f_unicos)
            if f_tit: st.session_state.eliminados['titulo'] = pd.read_csv(f_tit)
            if f_res: st.session_state.eliminados['resumen'] = pd.read_csv(f_res)
            if f_ina: st.session_state.eliminados['inaccesibles'] = pd.read_csv(f_ina)
            st.success("¡Sesión restaurada!")

# --- INTERFAZ DE FILTRADO CON PAGINACIÓN ---
if st.session_state.df_final is not None:
    st.title("🔍 Panel de Filtrado")
    
    # Buscador
    termino = st.text_input("Filtrar por palabra clave:")
    mask = st.session_state.df_final['title'].str.contains(termino, case=False, na=False) | \
           st.session_state.df_final['authors'].str.contains(termino, case=False, na=False)
    
    df_filtrado = st.session_state.df_final[mask]
    
    # --- LÓGICA DE PAGINACIÓN ---
    items_por_pagina = 20
    total_paginas = (len(df_filtrado) // items_por_pagina) + 1
    pagina_actual = st.number_input("Página", min_value=1, max_value=total_paginas, step=1)
    
    inicio = (pagina_actual - 1) * items_por_pagina
    fin = inicio + items_por_pagina
    
    st.write(f"Mostrando artículos {inicio} al {min(fin, len(df_filtrado))} de {len(df_filtrado)}")

    for idx, art in df_filtrado.iloc[inicio:fin].iterrows():
        with st.container():
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"### {art['title']}")
                st.caption(f"**Autores:** {art['authors']} | **Año:** {art['year']} | **Fuente:** {art.get('fuente', 'N/A')}")
                
                # Expandible para ver el resumen y editar datos
                with st.expander("📄 Ver Resumen y Detalles"):
                    # Editar DOI
                    curr_doi = str(art.get('doi', '') or '')
                    if curr_doi.lower() == "nan": curr_doi = ""
                    
                    nuevo_doi = st.text_input(f"DOI (ID {idx})", value=curr_doi, key=f"doi_{idx}")
                    if nuevo_doi != curr_doi:
                        st.session_state.df_final.at[idx, 'doi'] = nuevo_doi
                    
                    if nuevo_doi:
                        st.markdown(f"[🔗 Abrir DOI en pestaña nueva](https://doi.org/{nuevo_doi})")
                    
                    # Editar Resumen
                    curr_abs = str(art.get('abstract', '') or '')
                    if curr_abs.lower() == "nan": curr_abs = ""
                    
                    nuevo_abs = st.text_area("Abstract", value=curr_abs, height=150, key=f"abs_{idx}")
                    if nuevo_abs != curr_abs:
                        st.session_state.df_final.at[idx, 'abstract'] = nuevo_abs

            with col_actions:
                st.write("") # Espaciador visual
                # Botón Título
                if st.button("🗑️ Título", key=f"btn_tit_{idx}", use_container_width=True):
                    st.session_state.eliminados['titulo'] = pd.concat([st.session_state.eliminados['titulo'], art.to_frame().T])
                    st.session_state.df_final.drop(idx, inplace=True)
                    st.rerun()
                
                # Botón Inaccesible (Recuperado)
                if st.button("🚫 Inaccesible", key=f"btn_ina_{idx}", use_container_width=True):
                    st.session_state.eliminados['inaccesibles'] = pd.concat([st.session_state.eliminados['inaccesibles'], art.to_frame().T])
                    st.session_state.df_final.drop(idx, inplace=True)
                    st.rerun()

                # Botón Resumen
                if st.button("❌ Resumen", key=f"btn_res_{idx}", use_container_width=True):
                    st.session_state.eliminados['resumen'] = pd.concat([st.session_state.eliminados['resumen'], art.to_frame().T])
                    st.session_state.df_final.drop(idx, inplace=True)
                    st.rerun()
            
            st.markdown("---")

    # --- BOTONES DE DESCARGA ---
    st.divider()
    st.subheader("📥 Exportar Resultados")
    
    # Función auxiliar para la descarga
    def convert_df(df):
        return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

    # Fila 1: Resultados finales y duplicados
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("✅ **Artículos Incluidos**")
        st.download_button(
            label=f"Descargar Finales ({len(st.session_state.df_final)})",
            data=convert_df(st.session_state.df_final),
            file_name="articulos_finales_inclusion.csv",
            mime="text/csv",
            key="btn_final"
        )
    with col_b:
        st.write("👯 **Duplicados Detectados**")
        st.download_button(
            label=f"Descargar Duplicados ({len(st.session_state.eliminados['duplicados'])})",
            data=convert_df(st.session_state.eliminados['duplicados']),
            file_name="eliminados_duplicados.csv",
            mime="text/csv",
            key="btn_dup"
        )

    st.write("---")
    st.write("❌ **Artículos Excluidos por Criterios**")
    
    # Fila 2: Criterios específicos
    c1, c2, c3 = st.columns(3)
    
    with c1:
        n_tit = len(st.session_state.eliminados['titulo'])
        st.download_button(
            label=f"Excluidos por Título ({n_tit})",
            data=convert_df(st.session_state.eliminados['titulo']),
            file_name="excluidos_por_titulo.csv",
            mime="text/csv",
            disabled=(n_tit == 0)
        )

    with c2:
        n_res = len(st.session_state.eliminados['resumen'])
        st.download_button(
            label=f"Excluidos por Resumen ({n_res})",
            data=convert_df(st.session_state.eliminados['resumen']),
            file_name="excluidos_por_resumen.csv",
            mime="text/csv",
            disabled=(n_res == 0)
        )

    with c3:
        n_ina = len(st.session_state.eliminados['inaccesibles'])
        st.download_button(
            label=f"Excluidos por Inaccesibilidad ({n_ina})",
            data=convert_df(st.session_state.eliminados['inaccesibles']),
            file_name="excluidos_por_inaccesibles.csv",
            mime="text/csv",
            disabled=(n_ina == 0)
        )