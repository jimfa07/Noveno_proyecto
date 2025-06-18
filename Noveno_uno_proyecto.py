import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import atexit
import io

# --- Configuración de Archivos ---
# Obtener el directorio actual del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Crear un subdirectorio 'data' si no existe
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Rutas completas a los archivos CSV
VENTAS_FILE = os.path.join(DATA_DIR, 'ventas.csv')
GASTOS_FILE = os.path.join(DATA_DIR, 'gastos.csv')


# --- Funciones de carga y guardado de datos (sin base de datos) ---
def cargar_ventas_desde_archivo():
    """Carga las ventas desde un archivo CSV. Si no existe, devuelve un DataFrame vacío."""
    if os.path.exists(VENTAS_FILE):
        try:
            df = pd.read_csv(VENTAS_FILE)
            # Asegúrate de que las columnas de fecha sean objetos date
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            return df
        except Exception as e:
            st.error(f"Error al cargar ventas desde {VENTAS_FILE}: {e}")
            return pd.DataFrame(columns=['fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'descuento',
                                         'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo'])
    return pd.DataFrame(columns=['fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'descuento',
                                 'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo'])

def cargar_gastos_desde_archivo():
    """Carga los gastos desde un archivo CSV. Si no existe, devuelve un DataFrame vacío."""
    if os.path.exists(GASTOS_FILE):
        try:
            df = pd.read_csv(GASTOS_FILE)
            # Asegúrate de que las columnas de fecha sean objetos date
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            return df
        except Exception as e:
            st.error(f"Error al cargar gastos desde {GASTOS_FILE}: {e}")
            return pd.DataFrame(columns=['fecha', 'calculo', 'descripcion', 'gasto', 'dinero'])
    return pd.DataFrame(columns=['fecha', 'calculo', 'descripcion', 'gasto', 'dinero'])

def guardar_dataframes_en_archivos():
    """Guarda los DataFrames de ventas y gastos en archivos CSV."""
    if 'ventas_raw_data' in st.session_state and not st.session_state.ventas_raw_data.empty:
        # Asegurarse de que la columna 'fecha' sea compatible con .to_csv (string o datetime)
        df_to_save_ventas = st.session_state.ventas_raw_data.copy()
        if 'fecha' in df_to_save_ventas.columns:
             # Convertir solo si es necesario (ej. si son objetos date.date y no datetime)
            df_to_save_ventas['fecha'] = pd.to_datetime(df_to_save_ventas['fecha']).dt.strftime('%Y-%m-%d')
        df_to_save_ventas.to_csv(VENTAS_FILE, index=False)
        # Si prefieres Excel, descomenta la siguiente línea y comenta la anterior:
        # st.session_state.ventas_raw_data.to_excel(VENTAS_FILE.replace(".csv", ".xlsx"), index=False, engine='xlsxwriter')
    
    if 'gastos_raw_data' in st.session_state and not st.session_state.gastos_raw_data.empty:
        # Asegurarse de que la columna 'fecha' sea compatible con .to_csv (string o datetime)
        df_to_save_gastos = st.session_state.gastos_raw_data.copy()
        if 'fecha' in df_to_save_gastos.columns:
            df_to_save_gastos['fecha'] = pd.to_datetime(df_to_save_gastos['fecha']).dt.strftime('%Y-%m-%d')
        df_to_save_gastos.to_csv(GASTOS_FILE, index=False)
        # Si prefieres Excel, descomenta la siguiente línea y comenta la anterior:
        # st.session_state.gastos_raw_data.to_excel(GASTOS_FILE.replace(".csv", ".xlsx"), index=False, engine='xlsxwriter')

# Registrar la función de guardado para que se ejecute al finalizar la aplicación
atexit.register(guardar_dataframes_en_archivos)

# --- Funciones para DataFrames (actualizadas para usar st.session_state directamente) ---
def get_ventas_df_processed():
    """Procesa el DataFrame de ventas para su visualización desde raw data."""
    df = st.session_state.ventas_raw_data.copy()
    if not df.empty:
        # Convertir a formato de fecha localizable para visualización
        if 'fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['fecha']).dt.date
        else: # Si por alguna razón falta 'fecha' en la carga inicial, crea una columna de fecha ficticia
            df['Fecha'] = date.today() 
            st.warning("Columna 'fecha' no encontrada en ventas_raw_data. Usando fecha actual.")
        
        df = df.rename(columns={
            'fecha': 'Fecha DB', 'cliente': 'Cliente', 'tipo': 'Tipo', 'cantidad': 'Cantidad',
            'libras': 'Libras', 'descuento': 'Descuento', 'libras_netas': 'Libras_netas',
            'precio': 'Precio', 'total_a_cobrar': 'Total_a_cobrar', 'pago_cliente': 'Pago_Cliente',
            'saldo': 'Saldo'
        })
        # Ordenar por fecha y luego por cliente para consistencia
        df = df.sort_values(by=['Fecha', 'Cliente'], ascending=[False, True])
    return df

def get_gastos_df_processed():
    """Procesa el DataFrame de gastos para su visualización desde raw data."""
    df = st.session_state.gastos_raw_data.copy()
    if not df.empty:
        if 'fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['fecha']).dt.date
        else: # Si por alguna razón falta 'fecha' en la carga inicial, crea una columna de fecha ficticia
            df['Fecha'] = date.today()
            st.warning("Columna 'fecha' no encontrada en gastos_raw_data. Usando fecha actual.")

        df = df.rename(columns={
            'fecha': 'Fecha DB', 'calculo': 'Calculo', 'descripcion': 'Descripcion',
            'gasto': 'Gasto', 'dinero': 'Dinero'
        })
        # Ordenar por fecha
        df = df.sort_values(by='Fecha', ascending=False)
    return df

def guardar_venta(venta_data):
    """Guarda una nueva venta en el DataFrame de session_state y luego en archivo."""
    nueva_venta_df = pd.DataFrame([venta_data])
    # Asegúrate de que las columnas coincidan para la concatenación
    st.session_state.ventas_raw_data = pd.concat([nueva_venta_df, st.session_state.ventas_raw_data], ignore_index=True)
    guardar_dataframes_en_archivos() # Guardar inmediatamente en archivo
    return True

def guardar_gasto(gasto_data):
    """Guarda un nuevo gasto en el DataFrame de session_state y luego en archivo."""
    nuevo_gasto_df = pd.DataFrame([gasto_data])
    # Asegúrate de que las columnas coincidan para la concatenación
    st.session_state.gastos_raw_data = pd.concat([nuevo_gasto_df, st.session_state.gastos_raw_data], ignore_index=True)
    guardar_dataframes_en_archivos() # Guardar inmediatamente en archivo
    return True

def limpiar_ventas():
    """Elimina todas las ventas del DataFrame y del archivo."""
    st.session_state.ventas_raw_data = pd.DataFrame(columns=['fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'descuento',
                                                             'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo'])
    guardar_dataframes_en_archivos() # Guardar el DataFrame vacío
    if os.path.exists(VENTAS_FILE):
        os.remove(VENTAS_FILE) # Eliminar el archivo físicamente
    return True

def limpiar_gastos():
    """Elimina todos los gastos del DataFrame y del archivo."""
    st.session_state.gastos_raw_data = pd.DataFrame(columns=['fecha', 'calculo', 'descripcion', 'gasto', 'dinero'])
    guardar_dataframes_en_archivos() # Guardar el DataFrame vacío
    if os.path.exists(GASTOS_FILE):
        os.remove(GASTOS_FILE) # Eliminar el archivo físicamente
    return True

# --- Funciones para editar y eliminar datos (NUEVAS) ---

def actualizar_venta(index, updated_data):
    """Actualiza una venta existente en el DataFrame de session_state."""
    for col, val in updated_data.items():
        if col == 'fecha':
            st.session_state.ventas_raw_data.loc[index, col] = pd.to_datetime(val).date()
        else:
            st.session_state.ventas_raw_data.loc[index, col] = val
    # Recalcular campos derivados si es necesario
    libras = st.session_state.ventas_raw_data.loc[index, 'libras']
    descuento = st.session_state.ventas_raw_data.loc[index, 'descuento']
    precio = st.session_state.ventas_raw_data.loc[index, 'precio']
    pago_cliente = st.session_state.ventas_raw_data.loc[index, 'pago_cliente']

    st.session_state.ventas_raw_data.loc[index, 'libras_netas'] = calcular_libras_netas(libras, descuento)
    st.session_state.ventas_raw_data.loc[index, 'total_a_cobrar'] = calcular_total_cobrar(st.session_state.ventas_raw_data.loc[index, 'libras_netas'], precio)
    st.session_state.ventas_raw_data.loc[index, 'saldo'] = calcular_saldo(st.session_state.ventas_raw_data.loc[index, 'total_a_cobrar'], pago_cliente)

    guardar_dataframes_en_archivos()
    st.session_state.ventas_data = get_ventas_df_processed() # Actualiza el df procesado
    return True

def eliminar_ventas_seleccionadas(indices):
    """Elimina ventas seleccionadas del DataFrame de session_state."""
    st.session_state.ventas_raw_data = st.session_state.ventas_raw_data.drop(indices).reset_index(drop=True)
    guardar_dataframes_en_archivos()
    st.session_state.ventas_data = get_ventas_df_processed() # Actualiza el df procesado
    return True

def actualizar_gasto(index, updated_data):
    """Actualiza un gasto existente en el DataFrame de session_state."""
    for col, val in updated_data.items():
        if col == 'fecha':
            st.session_state.gastos_raw_data.loc[index, col] = pd.to_datetime(val).date()
        else:
            st.session_state.gastos_raw_data.loc[index, col] = val
    guardar_dataframes_en_archivos()
    st.session_state.gastos_data = get_gastos_df_processed() # Actualiza el df procesado
    return True

def eliminar_gastos_seleccionados(indices):
    """Elimina gastos seleccionados del DataFrame de session_state."""
    st.session_state.gastos_raw_data = st.session_state.gastos_raw_data.drop(indices).reset_index(drop=True)
    guardar_dataframes_en_archivos()
    st.session_state.gastos_data = get_gastos_df_processed() # Actualiza el df procesado
    return True


# --- Inicialización principal ---
st.title("🐔 Sistema de Gestión de Ventas de Aves")

# Inicializar datos en session state cargando desde archivos
# Se mantienen dos DataFrames: uno 'raw' para guardar y otro 'data' para visualizar
if 'ventas_raw_data' not in st.session_state:
    st.session_state.ventas_raw_data = cargar_ventas_desde_archivo()
if 'ventas_data' not in st.session_state: # Este será el DataFrame procesado para mostrar
    st.session_state.ventas_data = get_ventas_df_processed()

if 'gastos_raw_data' not in st.session_state:
    st.session_state.gastos_raw_data = cargar_gastos_desde_archivo()
if 'gastos_data' not in st.session_state: # Este será el DataFrame procesado para mostrar
    st.session_state.gastos_data = get_gastos_df_processed()


# --- Listas predefinidas ---
CLIENTES = [
    "D. Vicente", "D. Jorge", "D. Quinde", "Sra. Isabel", "Sra. Alba",
    "Sra Yolanda", "Sra Laura Mercado", "D. Segundo", "Legumbrero",
    "Peruana Posorja", "Sra. Sofia", "Sra. Jessica", "Sra Alado de Jessica",
    "Comedor Gordo Posorja", "Patitas Posorja", "Sra. Celeste", "Caro negro", "Tienda Isabel Posorja",
    "Carnicero Posorja", "Moreira","Senel", "Chuzos Narcisa", "Eddy", "D. Jonny", "D. Sra Madelyn", "Lobo Mercado"
]

TIPOS_AVE = ["Pollo", "Gallina"]

CATEGORIAS_GASTO = [
    "G. Alimentación", "G. Transporte", "G. Producción", "G. Salud",
    "G. Educación", "G. Mano de obra", "G. Pérdida", "G. Varios", "Otros Gastos"
]

# --- Funciones de formateo y cálculo ---
def formatear_moneda(valor):
    """Formatea un valor numérico como una cadena de moneda."""
    try:
        return f"${float(valor):,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def calcular_libras_netas(libras, descuento):
    """Calcula las libras netas."""
    try:
        return round(float(libras) - float(descuento), 2)
    except:
        return 0.0

def calcular_total_cobrar(libras_netas, precio):
    """Calcula el total a cobrar."""
    try:
        return round(float(libras_netas) * float(precio), 2)
    except:
        return 0.0

def calcular_saldo(total_cobrar, pago_cliente):
    """Calcula el saldo pendiente."""
    try:
        return round(float(total_cobrar) - float(pago_cliente), 2)
    except:
        return 0.0

def analizar_alertas_clientes(ventas_df):
    """Analiza el DataFrame de ventas para identificar clientes con alertas."""
    if ventas_df.empty:
        return pd.DataFrame()

    # Asegúrate de trabajar con una copia para evitar SettingWithCopyWarning
    df_temp = ventas_df.copy()
    # Asegurarse de que la columna 'Fecha' sea de tipo datetime para operaciones de fecha
    if 'Fecha' in df_temp.columns:
        df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha'])
    else: # Fallback si 'Fecha' no se creó correctamente
        st.warning("Columna 'Fecha' no encontrada en df_temp para alertas. Algunas alertas podrían no ser precisas.")
        df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha DB']) # Usar 'Fecha DB' que es la original

    alertas = []

    for cliente in df_temp['Cliente'].unique():
        cliente_ventas = df_temp[df_temp['Cliente'] == cliente].copy()
        cliente_ventas = cliente_ventas.sort_values('Fecha')

        # Convertir 'Saldo' a numérico antes de sumar.
        # Es crucial que esta columna tenga el formato de moneda quitado si está presente.
        cliente_ventas['Saldo_num'] = cliente_ventas['Saldo'].apply(
            lambda x: float(str(x).replace('$', '').replace(',', '')) if isinstance(x, (str, float, int)) else x
        )
        saldo_total = cliente_ventas['Saldo_num'].sum()

        debe_mas_10 = saldo_total > 10

        dias_consecutivos = 0
        # Filtrar solo fechas con saldo positivo
        fechas_con_saldo = cliente_ventas[cliente_ventas['Saldo_num'] > 0]['Fecha'].dt.date.unique()

        if len(fechas_con_saldo) >= 2:
            fechas_ordenadas = sorted(list(fechas_con_saldo))
            consecutivos_actual = 1
            max_consecutivos = 1

            for i in range(1, len(fechas_ordenadas)):
                if (fechas_ordenadas[i] - fechas_ordenadas[i-1]).days == 1:
                    consecutivos_actual += 1
                    max_consecutivos = max(max_consecutivos, consecutivos_actual)
                else:
                    consecutivos_actual = 1

            dias_consecutivos = max_consecutivos

        if debe_mas_10 or dias_consecutivos >= 2:
            ultima_fecha = cliente_ventas['Fecha'].max().strftime('%Y-%m-%d')

            motivos = []
            if debe_mas_10:
                motivos.append(f"Debe más de ${saldo_total:.2f}")
            if dias_consecutivos >= 2:
                motivos.append(f"Saldo por {dias_consecutivos} día(s) consecutivo(s)")

            alertas.append({
                'Cliente': cliente,
                'Saldo_Total': saldo_total,
                'Ultima_Venta': ultima_fecha,
                'Motivo_Alerta': " | ".join(motivos),
                'Prioridad': 'Alta' if debe_mas_10 and dias_consecutivos >= 2 else 'Media'
            })

    return pd.DataFrame(alertas)


# --- SECCIÓN 1: TABLA DE VENTAS ---
st.header("📊 Registro de Ventas")

st.divider()
### 🚨 Alertas de Clientes
st.subheader("🚨 Alertas de Clientes")
alertas_df = analizar_alertas_clientes(st.session_state.ventas_data)
if not alertas_df.empty:
    st.dataframe(alertas_df, use_container_width=True, hide_index=True)
    st.warning("Revisa a los clientes listados para gestionar sus saldos.")
else:
    st.info("🎉 ¡No hay alertas de clientes pendientes! Todos los saldos al día.")

st.divider()

### ➕ Agregar Nueva Venta
with st.expander("📝 Formulario de Nueva Venta", expanded=False): # Cambiado a False para que el formulario esté colapsado por defecto
    col1, col2, col3, col4 = st.columns(4)
    
    # Inicializar valores en session_state para que los campos del formulario puedan resetearse
    # Estos son solo para el estado de los widgets, no los datos reales
    if 'cantidad_venta_val' not in st.session_state: st.session_state['cantidad_venta_val'] = 0
    if 'libras_venta_val' not in st.session_state: st.session_state['libras_venta_val'] = 0.0
    if 'descuento_venta_val' not in st.session_state: st.session_state['descuento_venta_val'] = 0.0
    if 'precio_venta_val' not in st.session_state: st.session_state['precio_venta_val'] = 0.0
    if 'pago_venta_val' not in st.session_state: st.session_state['pago_venta_val'] = 0.0
    if 'cliente_venta_val' not in st.session_state: st.session_state['cliente_venta_val'] = CLIENTES[0]
    if 'tipo_venta_val' not in st.session_state: st.session_state['tipo_venta_val'] = TIPOS_AVE[0]

    with col1:
        fecha_venta = st.date_input("Fecha", value=date.today(), key="fecha_venta")
        cliente = st.selectbox("Cliente", CLIENTES, key="cliente_venta_input", index=CLIENTES.index(st.session_state['cliente_venta_val']))
        tipo_ave = st.selectbox("Tipo", TIPOS_AVE, key="tipo_venta_input", index=TIPOS_AVE.index(st.session_state['tipo_venta_val']))
    
    with col2:
        cantidad = st.number_input("Cantidad", min_value=0, value=st.session_state['cantidad_venta_val'], step=1, key="cantidad_venta_input")
        libras = st.number_input("Libras", min_value=0.0, value=st.session_state['libras_venta_val'], step=0.1, format="%.2f", key="libras_venta_input")
        descuento = st.number_input("Descuento", min_value=0.0, value=st.session_state['descuento_venta_val'], step=0.1, format="%.2f", key="descuento_venta_input")
    
    with col3:
        libras_netas = calcular_libras_netas(libras, descuento)
        st.info(f"**Libras netas:** {libras_netas:.2f}") 
        
        precio = st.number_input("Precio ($)", min_value=0.0, value=st.session_state['precio_venta_val'], step=0.01, format="%.2f", key="precio_venta_input")
    
    with col4:
        total_cobrar = calcular_total_cobrar(libras_netas, precio)
        st.info(f"**Total a cobrar:** {formatear_moneda(total_cobrar)}")
        
        pago_cliente = st.number_input("Pago - Cliente ($)", min_value=0.0, value=st.session_state['pago_venta_val'], step=0.01, format="%.2f", key="pago_venta_input")
        
        saldo = calcular_saldo(total_cobrar, pago_cliente)
        st.info(f"**Saldo:** {formatear_moneda(saldo)}")
    
    if st.button("💾 Agregar Venta", type="primary", use_container_width=True):
        if cantidad > 0 and libras > 0 and precio > 0:
            venta_data = {
                'fecha': fecha_venta, 'cliente': cliente, 'tipo': tipo_ave,
                'cantidad': cantidad, 'libras': libras, 'descuento': descuento,
                'libras_netas': libras_netas, 'precio': precio,
                'total_a_cobrar': total_cobrar, 'pago_cliente': pago_cliente, 'saldo': saldo
            }
            
            if guardar_venta(venta_data): # Llama a la función que guarda en session_state y archivo
                st.session_state.ventas_data = get_ventas_df_processed() # Actualiza el df procesado
                st.success(f"✅ Venta para **'{cliente}'** guardada exitosamente.")
            else:
                st.error(f"❌ Error al guardar la venta para **'{cliente}'**.")
            
            # Resetear valores del formulario usando keys de session_state
            st.session_state['cantidad_venta_val'] = 0
            st.session_state['libras_venta_val'] = 0.0
            st.session_state['descuento_venta_val'] = 0.0
            st.session_state['precio_venta_val'] = 0.0
            st.session_state['pago_venta_val'] = 0.0
            st.session_state['cliente_venta_val'] = CLIENTES[0] 
            st.session_state['tipo_venta_val'] = TIPOS_AVE[0]   
            
            st.rerun() # Recarga la página para mostrar los cambios y resetear el formulario
        else:
            st.error("❌ Por favor complete los campos obligatorios: **Cantidad**, **Libras**, **Precio**.")

st.divider()

### 📋 Historial de Ventas (con edición y eliminación)
if not st.session_state.ventas_data.empty:
    st.subheader("📋 Historial de Ventas (Editar / Eliminar)")
    
    # Crear un DataFrame para la edición con una columna 'Seleccionar'
    df_editable_ventas = st.session_state.ventas_raw_data.copy()
    
    # Asegúrate de que las columnas de fecha sean objetos date para el editor
    if 'fecha' in df_editable_ventas.columns:
        df_editable_ventas['fecha'] = pd.to_datetime(df_editable_ventas['fecha']).dt.date

    # Configurar el Data Editor para permitir la selección de filas
    edited_df_ventas = st.data_editor(
        df_editable_ventas,
        key="ventas_data_editor",
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False # Mostrar índice para facilitar la eliminación
    )

    # Detección de cambios y actualización
    if st.session_state.ventas_data_editor['edited_rows']:
        for index, updates in st.session_state.ventas_data_editor['edited_rows'].items():
            if actualizar_venta(index, updates):
                st.success(f"✅ Venta en la fila {index+1} actualizada exitosamente.")
                st.session_state.ventas_data = get_ventas_df_processed() # Actualizar el df procesado
                # st.rerun() # Opcional: recargar la página para ver los cambios inmediatamente

    # Botón de eliminación
    if st.session_state.ventas_data_editor['deleted_rows']:
        st.warning(f"⚠️ Ha seleccionado {len(st.session_state.ventas_data_editor['deleted_rows'])} fila(s) para eliminar. ¿Está seguro?")
        if st.button(f"🚨 Confirmar Eliminación de Venta(s) Seleccionada(s) ({len(st.session_state.ventas_data_editor['deleted_rows'])})", type="danger", key="confirm_delete_selected_ventas"):
            if eliminar_ventas_seleccionadas(st.session_state.ventas_data_editor['deleted_rows']):
                st.success(f"✅ Venta(s) eliminada(s) exitosamente.")
                st.session_state.ventas_data = get_ventas_df_processed()
                st.rerun() # Recargar para reflejar la eliminación
            else:
                st.error("❌ Error al eliminar la(s) venta(s).")
    
    # Resumen de ventas (usando el DataFrame raw actualizado para cálculos)
    total_ventas = st.session_state.ventas_raw_data['total_a_cobrar'].sum()
    total_pagos = st.session_state.ventas_raw_data['pago_cliente'].sum()
    saldo_pendiente = st.session_state.ventas_raw_data['saldo'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total Ventas", formatear_moneda(total_ventas))
    with col2:
        st.metric("💵 Total Pagos Recibidos", formatear_moneda(total_pagos))
    with col3:
        st.metric("📈 Saldo Pendiente General", formatear_moneda(saldo_pendiente))

    st.divider()
    ### 📤 Opciones de Importación y Exportación de Ventas
    st.subheader("📥 Exportar / 📤 Importar Ventas")
    col_exp_imp_ventas_1, col_exp_imp_ventas_2 = st.columns(2)

    with col_exp_imp_ventas_1:
        # Botón para descargar a Excel
        df_for_download_ventas = st.session_state.ventas_raw_data.copy()
        if not df_for_download_ventas.empty:
            df_for_download_ventas['fecha'] = pd.to_datetime(df_for_download_ventas['fecha']).dt.strftime('%Y-%m-%d') # Formato de fecha para Excel
            
            # Create an in-memory Excel file
            output = io.BytesIO()
            df_for_download_ventas.to_excel(output, index=False, engine='xlsxwriter')
            processed_data = output.getvalue()
            
            st.download_button(
                label="⬇️ Descargar Ventas a Excel",
                data=processed_data, # Directly provide the Excel bytes
                file_name="ventas_aves.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga todas las ventas registradas en formato Excel."
            )
        else:
            st.info("No hay datos de ventas para descargar.")

    with col_exp_imp_ventas_2:
        # Cargador de archivos para importar ventas
        uploaded_file_ventas = st.file_uploader("⬆️ Importar Ventas desde Excel/CSV", type=["xlsx", "csv"], key="upload_ventas_excel")
        if uploaded_file_ventas:
            try:
                if uploaded_file_ventas.name.endswith('.xlsx'):
                    df_imported_ventas = pd.read_excel(uploaded_file_ventas)
                else: # .csv
                    df_imported_ventas = pd.read_csv(uploaded_file_ventas)
                
                # Nombres de columnas esperados (minúsculas y sin espacios)
                expected_cols_raw_ventas = [
                    'fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'descuento', 
                    'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo'
                ]
                
                # Convertir nombres de columnas a minúsculas y sin espacios para validación
                df_imported_ventas.columns = df_imported_ventas.columns.str.lower().str.replace(' ', '_')

                # Validar que las columnas necesarias existan
                if not all(col in df_imported_ventas.columns for col in expected_cols_raw_ventas):
                    st.error(f"❌ El archivo importado no tiene las columnas requeridas o tienen nombres incorrectos. Asegúrate de que existan: {', '.join(expected_cols_raw_ventas)}")
                else:
                    # Convertir el DataFrame importado para que coincida con el formato de fecha esperado
                    # y asegurar tipos de datos correctos antes de concatenar
                    for col in ['cantidad']:
                        if col in df_imported_ventas.columns:
                            df_imported_ventas[col] = pd.to_numeric(df_imported_ventas[col], errors='coerce').fillna(0).astype(int)
                    for col in ['libras', 'descuento', 'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo']:
                         if col in df_imported_ventas.columns:
                            df_imported_ventas[col] = pd.to_numeric(df_imported_ventas[col], errors='coerce').fillna(0.0).round(2)
                    
                    if 'fecha' in df_imported_ventas.columns:
                        df_imported_ventas['fecha'] = pd.to_datetime(df_imported_ventas['fecha'], errors='coerce').dt.date
                        df_imported_ventas.dropna(subset=['fecha'], inplace=True) # Eliminar filas sin fecha válida
                    else:
                        st.error("❌ La columna 'fecha' es obligatoria para importar ventas.")
                        df_imported_ventas = pd.DataFrame() # Vaciar el DF si no hay fecha válida

                    if not df_imported_ventas.empty:
                        # Filtrar solo las columnas que necesitamos para la concatenación y reordenar
                        df_imported_ventas = df_imported_ventas[expected_cols_raw_ventas]

                        # Concatena el nuevo DataFrame con el existente
                        initial_rows = len(st.session_state.ventas_raw_data)
                        st.session_state.ventas_raw_data = pd.concat([st.session_state.ventas_raw_data, df_imported_ventas], ignore_index=True)
                        # Eliminar duplicados basándose en un subconjunto de columnas que definan una venta única
                        st.session_state.ventas_raw_data.drop_duplicates(subset=['fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'precio'], keep='first', inplace=True) 
                        
                        rows_imported = len(st.session_state.ventas_raw_data) - initial_rows

                        if rows_imported > 0:
                            guardar_dataframes_en_archivos() # Guardar después de la importación
                            st.session_state.ventas_data = get_ventas_df_processed() # Actualiza el df procesado
                            st.success(f"✅ Se importaron **{rows_imported}** ventas exitosamente desde el archivo.")
                            st.rerun()
                        else:
                            st.info("No se encontraron ventas válidas o nuevas en el archivo para importar.")
                    else:
                        st.info("El archivo importado está vacío o no contiene datos válidos.")

            except Exception as e:
                st.error(f"❌ Error al leer el archivo de ventas: {e}. Asegúrate de que sea un archivo .xlsx o .csv válido y tenga el formato correcto.")
else:
    st.info("📝 No hay ventas registradas. ¡Empieza a agregar ventas usando el formulario de arriba!")


# Botón para limpiar datos de ventas
if not st.session_state.ventas_raw_data.empty: # Usar raw_data para la condición
    with st.expander("🗑️ Opciones Avanzadas de Ventas (Eliminar Datos)"):
        st.error("¡Esta acción eliminará PERMANENTEMENTE todas las ventas! Úsala con extrema precaución y solo si estás seguro.")
        # Primer nivel de confirmación
        if st.button("🔴 Eliminar TODAS las Ventas (Paso 1: Confirmar)", type="secondary", use_container_width=True, key="limpiar_ventas_confirm_step1"):
            st.session_state['confirm_delete_ventas'] = True
            st.warning("⚠️ ¡Estás a punto de eliminar todos los datos de ventas! Haz clic en el botón rojo de abajo para confirmar la eliminación permanente.")
        
        # Segundo nivel de confirmación
        if st.session_state.get('confirm_delete_ventas', False):
            if st.button("🚨 CONFIRMAR ELIMINACIÓN PERMANENTE DE VENTAS 🚨", type="danger", use_container_width=True, key="limpiar_ventas_confirm_step2"):
                if limpiar_ventas(): # Llama a la función de limpieza
                    st.session_state.ventas_data = get_ventas_df_processed() # Actualiza el df procesado
                    st.success("✅ Todas las ventas han sido eliminadas exitosamente.")
                else:
                    st.error("❌ Ocurrió un error al intentar eliminar las ventas.")
                st.session_state['confirm_delete_ventas'] = False # Resetear confirmación
                st.rerun()
            if st.button("Cancelar Eliminación de Ventas", use_container_width=True, key="cancel_delete_ventas_form"):
                st.session_state['confirm_delete_ventas'] = False
                st.info("Operación de limpieza de ventas cancelada.")
                st.rerun()

st.divider()

# --- SECCIÓN 2: TABLA DE GASTOS ---
st.header("💸 Control de Gastos")

st.divider()
### ➕ Agregar Nuevo Gasto
with st.expander("📝 Formulario de Nuevo Gasto", expanded=False): # Cambiado a False para que el formulario esté colapsado por defecto
    col1, col2, col3 = st.columns(3)
    
    # Inicializar valores en session_state
    if 'calculo_gasto_val' not in st.session_state: st.session_state['calculo_gasto_val'] = 0.0
    if 'descripcion_gasto_val' not in st.session_state: st.session_state['descripcion_gasto_val'] = ''
    if 'dinero_gasto_val' not in st.session_state: st.session_state['dinero_gasto_val'] = 0.0
    if 'categoria_gasto_val' not in st.session_state: st.session_state['categoria_gasto_val'] = CATEGORIAS_GASTO[0]

    with col1:
        fecha_gasto = st.date_input("Fecha", value=date.today(), key="fecha_gasto")
        calculo = st.number_input("Cálculo (Opcional)", value=st.session_state['calculo_gasto_val'], step=0.01, format="%.2f", key="calculo_gasto_input")
    
    with col2:
        descripcion = st.text_input("Descripción (Detalle del gasto)", value=st.session_state['descripcion_gasto_val'], key="descripcion_gasto_input")
        categoria_gasto = st.selectbox("Categoría de Gasto", CATEGORIAS_GASTO, key="categoria_gasto_input", index=CATEGORIAS_GASTO.index(st.session_state['categoria_gasto_val']))
    
    with col3:
        dinero = st.number_input("Dinero ($) (Monto del gasto)", min_value=0.0, value=st.session_state['dinero_gasto_val'], step=0.01, format="%.2f", key="dinero_gasto_input")
    
    if st.button("💾 Agregar Gasto", type="primary", use_container_width=True):
        if dinero > 0:
            gasto_data = {
                'fecha': fecha_gasto,
                'calculo': calculo,
                'descripcion': descripcion,
                'gasto': categoria_gasto,
                'dinero': dinero
            }
            
            if guardar_gasto(gasto_data): # Llama a la función que guarda en session_state y archivo
                st.session_state.gastos_data = get_gastos_df_processed() # Actualiza el df procesado
                st.success(f"✅ Gasto de **'{categoria_gasto}'** por {formatear_moneda(dinero)} guardado exitosamente.")
            else:
                st.error(f"❌ Error al guardar el gasto para **'{categoria_gasto}'**.")
            
            # Resetear valores del formulario
            st.session_state['calculo_gasto_val'] = 0.0
            st.session_state['descripcion_gasto_val'] = ""
            st.session_state['dinero_gasto_val'] = 0.0
            st.session_state['categoria_gasto_val'] = CATEGORIAS_GASTO[0]
            
            st.rerun()
        else:
            st.error("❌ Por favor, ingrese un valor de **Dinero** mayor a 0 para el gasto.")

st.divider()

### 📈 Historial de Gastos (con edición y eliminación)
if not st.session_state.gastos_data.empty:
    st.subheader("📈 Historial de Gastos (Editar / Eliminar)")

    # Crear un DataFrame para la edición con una columna 'Seleccionar'
    df_editable_gastos = st.session_state.gastos_raw_data.copy()

    # Asegúrate de que las columnas de fecha sean objetos date para el editor
    if 'fecha' in df_editable_gastos.columns:
        df_editable_gastos['fecha'] = pd.to_datetime(df_editable_gastos['fecha']).dt.date
    
    # Configurar el Data Editor para permitir la selección de filas
    edited_df_gastos = st.data_editor(
        df_editable_gastos,
        key="gastos_data_editor",
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False # Mostrar índice para facilitar la eliminación
    )

    # Detección de cambios y actualización
    if st.session_state.gastos_data_editor['edited_rows']:
        for index, updates in st.session_state.gastos_data_editor['edited_rows'].items():
            if actualizar_gasto(index, updates):
                st.success(f"✅ Gasto en la fila {index+1} actualizado exitosamente.")
                st.session_state.gastos_data = get_gastos_df_processed() # Actualizar el df procesado
                # st.rerun() # Opcional: recargar la página para ver los cambios inmediatamente

    # Botón de eliminación
    if st.session_state.gastos_data_editor['deleted_rows']:
        st.warning(f"⚠️ Ha seleccionado {len(st.session_state.gastos_data_editor['deleted_rows'])} fila(s) para eliminar. ¿Está seguro?")
        if st.button(f"🚨 Confirmar Eliminación de Gasto(s) Seleccionado(s) ({len(st.session_state.gastos_data_editor['deleted_rows'])})", type="danger", key="confirm_delete_selected_gastos"):
            if eliminar_gastos_seleccionados(st.session_state.gastos_data_editor['deleted_rows']):
                st.success(f"✅ Gasto(s) eliminados(s) exitosamente.")
                st.session_state.gastos_data = get_gastos_df_processed()
                st.rerun() # Recargar para reflejar la eliminación
            else:
                st.error("❌ Error al eliminar el(los) gasto(s).")
    
    # Resumen de gastos
    total_gastos = st.session_state.gastos_raw_data['dinero'].sum()
    st.metric("💸 Total Gastos Registrados", formatear_moneda(total_gastos))

    st.divider()
    ### 📤 Opciones de Importación y Exportación de Gastos
    st.subheader("📥 Exportar / 📤 Importar Gastos")
    col_exp_imp_gastos_1, col_exp_imp_gastos_2 = st.columns(2)

    with col_exp_imp_gastos_1:
        # Botón para descargar a Excel
        df_for_download_gastos = st.session_state.gastos_raw_data.copy()
        if not df_for_download_gastos.empty:
            df_for_download_gastos['fecha'] = pd.to_datetime(df_for_download_gastos['fecha']).dt.strftime('%Y-%m-%d') # Formato de fecha para Excel
            
            # Create an in-memory Excel file
            output_gastos = io.BytesIO()
            df_for_download_gastos.to_excel(output_gastos, index=False, engine='xlsxwriter')
            processed_data_gastos = output_gastos.getvalue()

            st.download_button(
                label="⬇️ Descargar Gastos a Excel",
                data=processed_data_gastos, # Directly provide the Excel bytes
                file_name="gastos_aves.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga todos los gastos registrados en formato Excel."
            )
        else:
            st.info("No hay datos de gastos para descargar.")

    with col_exp_imp_gastos_2:
        # Cargador de archivos para importar gastos
        uploaded_file_gastos = st.file_uploader("⬆️ Importar Gastos desde Excel/CSV", type=["xlsx", "csv"], key="upload_gastos_excel")
        if uploaded_file_gastos:
            try:
                if uploaded_file_gastos.name.endswith('.xlsx'):
                    df_imported_gastos = pd.read_excel(uploaded_file_gastos)
                else: # .csv
                    df_imported_gastos = pd.read_csv(uploaded_file_gastos)
                
                # Nombres de columnas esperados (minúsculas y sin espacios)
                expected_cols_raw_gastos = [
                    'fecha', 'calculo', 'descripcion', 'gasto', 'dinero'
                ]

                # Convertir nombres de columnas a minúsculas y sin espacios para validación
                df_imported_gastos.columns = df_imported_gastos.columns.str.lower().str.replace(' ', '_')

                # Validar que las columnas necesarias existan
                if not all(col in df_imported_gastos.columns for col in expected_cols_raw_gastos):
                    st.error(f"❌ El archivo importado no tiene las columnas requeridas o tienen nombres incorrectos. Asegúrate de que existan: {', '.join(expected_cols_raw_gastos)}")
                else:
                    # Convertir el DataFrame importado para que coincida con el formato de fecha esperado
                    # y asegurar tipos de datos correctos antes de concatenar
                    for col in ['calculo', 'dinero']:
                         if col in df_imported_gastos.columns:
                            df_imported_gastos[col] = pd.to_numeric(df_imported_gastos[col], errors='coerce').fillna(0.0).round(2)
                    
                    if 'fecha' in df_imported_gastos.columns:
                        df_imported_gastos['fecha'] = pd.to_datetime(df_imported_gastos['fecha'], errors='coerce').dt.date
                        df_imported_gastos.dropna(subset=['fecha'], inplace=True) # Eliminar filas sin fecha válida
                    else:
                        st.error("❌ La columna 'fecha' es obligatoria para importar gastos.")
                        df_imported_gastos = pd.DataFrame() # Vaciar el DF si no hay fecha válida


                    if not df_imported_gastos.empty:
                        # Filtrar solo las columnas que necesitamos para la concatenación
                        df_imported_gastos = df_imported_gastos[expected_cols_raw_gastos]

                        # Concatena el nuevo DataFrame con el existente
                        initial_rows = len(st.session_state.gastos_raw_data)
                        st.session_state.gastos_raw_data = pd.concat([st.session_state.gastos_raw_data, df_imported_gastos], ignore_index=True)
                        # Eliminar duplicados basándose en un subconjunto de columnas que definan un gasto único
                        st.session_state.gastos_raw_data.drop_duplicates(subset=['fecha', 'gasto', 'dinero'], keep='first', inplace=True) 
                        
                        rows_imported = len(st.session_state.gastos_raw_data) - initial_rows

                        if rows_imported > 0:
                            guardar_dataframes_en_archivos() # Guardar después de la importación
                            st.session_state.gastos_data = get_gastos_df_processed() # Actualiza el df procesado
                            st.success(f"✅ Se importaron **{rows_imported}** gastos exitosamente desde el archivo.")
                            st.rerun()
                        else:
                            st.info("No se encontraron gastos válidos o nuevos en el archivo para importar.")
                    else:
                        st.info("El archivo importado está vacío o no contiene datos válidos.")

            except Exception as e:
                st.error(f"❌ Error al leer el archivo de gastos: {e}. Asegúrate de que sea un archivo .xlsx o .csv válido y tenga el formato correcto.")
else:
    st.info("📝 No hay gastos registrados. ¡Empieza a agregar gastos usando el formulario de arriba!")

# Botón para limpiar datos de gastos
if not st.session_state.gastos_raw_data.empty: # Usar raw_data para la condición
    with st.expander("🗑️ Opciones Avanzadas de Gastos (Eliminar Datos)"):
        st.error("¡Esta acción eliminará PERMANENTEMENTE todos los gastos! Úsala con extrema precaución y solo si estás seguro.")
        # Primer nivel de confirmación
        if st.button("🔴 Eliminar TODOS los Gastos (Paso 1: Confirmar)", type="secondary", use_container_width=True, key="limpiar_gastos_confirm_step1"):
            st.session_state['confirm_delete_gastos'] = True
            st.warning("⚠️ ¡Estás a punto de eliminar todos los datos de gastos! Haz clic en el botón rojo de abajo para confirmar la eliminación permanente.")
        
        # Segundo nivel de confirmación
        if st.session_state.get('confirm_delete_gastos', False):
            if st.button("🚨 CONFIRMAR ELIMINACIÓN PERMANENTE DE GASTOS 🚨", type="danger", use_container_width=True, key="limpiar_gastos_confirm_step2"):
                if limpiar_gastos(): # Llama a la función de limpieza
                    st.session_state.gastos_data = get_gastos_df_processed() # Actualiza el df procesado
                    st.success("✅ Todos los gastos han sido eliminados exitosamente.")
                else:
                    st.error("❌ Ocurrió un error al intentar eliminar los gastos.")
                st.session_state['confirm_delete_gastos'] = False # Resetear confirmación
                st.rerun()
            if st.button("Cancelar Eliminación de Gastos", use_container_width=True, key="cancel_delete_gastos_form"):
                st.session_state['confirm_delete_gastos'] = False
                st.info("Operación de limpieza de gastos cancelada.")
                st.rerun()
