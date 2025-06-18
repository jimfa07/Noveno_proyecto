import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import base64
import io
import atexit

# --- 1. CONSTANTES Y CONFIGURACIÓN INICIAL ---
# Archivos para el Código 1 (Proveedores, Depósitos, Notas de Débito)
DATA_FILE = "registro_data.pkl"
DEPOSITS_FILE = "registro_depositos.pkl"
DEBIT_NOTES_FILE = "registro_notas_debito.pkl"

# Archivos para el Código 2 (Ventas y Gastos)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
VENTAS_FILE = os.path.join(DATA_DIR, 'ventas.csv')
GASTOS_FILE = os.path.join(DATA_DIR, 'gastos.csv')

# Constantes del Código 1
INITIAL_ACCUMULATED_BALANCE = 176.01
PRODUCT_NAME = "Pollo"
LBS_PER_KG = 2.20462
PROVEEDORES = ["LIRIS SA", "Gallina 1", "Monze Anzules", "Medina"]
TIPOS_DOCUMENTO = ["Factura", "Nota de debito", "Nota de credito"]
AGENCIAS = [
    "Cajero Automatico Pichincha", "Cajero Automatico Pacifico",
    "Cajero Automatico Guayaquil", "Cajero Automatico Bolivariano",
    "Banco Pichincha", "Banco del Pacifico", "Banco de Guayaquil",
    "Banco Bolivariano"
]

# Constantes del Código 2
CLIENTES = [
    "D. Vicente", "D. Jorge", "D. Quinde", "Sra. Isabel", "Sra. Alba",
    "Sra Yolanda", "Sra Laura Mercado", "D. Segundo", "Legumbrero",
    "Peruana Posorja", "Sra. Sofia", "Sra. Jessica", "Sra Alado de Jessica",
    "Comedor Gordo Posorja", "Patitas Posorja", "Sra. Celeste", "Caro negro",
    "Tienda Isabel Posorja", "Carnicero Posorja", "Moreira", "Senel",
    "Chuzos Narcisa", "Eddy", "D. Jonny", "D. Sra Madelyn", "Lobo Mercado"
]
TIPOS_AVE = ["Pollo", "Gallina"]
CATEGORIAS_GASTO = [
    "G. Alimentación", "G. Transporte", "G. Producción", "G. Salud",
    "G. Educación", "G. Mano de obra", "G. Pérdida", "G. Varios", "Otros Gastos"
]

# Columnas esperadas para los DataFrames
COLUMNS_DATA = [
    "N", "Fecha", "Proveedor", "Producto", "Cantidad",
    "Peso Salida (kg)", "Peso Entrada (kg)", "Tipo Documento",
    "Cantidad de gavetas", "Precio Unitario ($)", "Promedio",
    "Kilos Restantes", "Libras Restantes", "Total ($)",
    "Monto Deposito", "Saldo diario", "Saldo Acumulado"
]
COLUMNS_DEPOSITS = ["Fecha", "Empresa", "Agencia", "Monto", "Documento", "N"]
COLUMNS_DEBIT_NOTES = ["Fecha", "Libras calculadas", "Descuento", "Descuento posible", "Descuento real"]
COLUMNS_VENTAS = [
    'fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'descuento',
    'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo'
]
COLUMNS_GASTOS = ['fecha', 'calculo', 'descripcion', 'gasto', 'dinero']

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Sistema de Gestión de Proveedores y Ventas - Producto Pollo",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. FUNCIONES DE CARGA Y GUARDADO DE DATOS ---
@st.cache_data(show_spinner=False)
def load_dataframe(file_path, default_columns, date_columns=None):
    """Carga un DataFrame desde un archivo pickle o CSV, o crea uno vacío."""
    if os.path.exists(file_path):
        try:
            if file_path.endswith('.pkl'):
                df = pd.read_pickle(file_path)
            else:  # CSV
                df = pd.read_csv(file_path)
            if date_columns:
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
            for col in default_columns:
                if col not in df.columns:
                    df[col] = None
            return df[default_columns]
        except Exception as e:
            st.error(f"Error al cargar {file_path}: {e}. Creando DataFrame vacío.")
            return pd.DataFrame(columns=default_columns)
    return pd.DataFrame(columns=default_columns)

def save_dataframe(df, file_path):
    """Guarda un DataFrame en un archivo pickle o CSV."""
    try:
        if file_path.endswith('.pkl'):
            df.to_pickle(file_path)
        else:  # CSV
            df_to_save = df.copy()
            if 'fecha' in df_to_save.columns:
                df_to_save['fecha'] = pd.to_datetime(df_to_save['fecha']).dt.strftime('%Y-%m-%d')
            df_to_save.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar {file_path}: {e}")
        return False

def guardar_dataframes_en_archivos():
    """Guarda los DataFrames de ventas y gastos en archivos CSV."""
    if 'ventas_raw_data' in st.session_state and not st.session_state.ventas_raw_data.empty:
        save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE)
    if 'gastos_raw_data' in st.session_state and not st.session_state.gastos_raw_data.empty:
        save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE)

atexit.register(guardar_dataframes_en_archivos)

# --- 3. FUNCIONES DE INICIALIZACIÓN DEL ESTADO ---
def initialize_session_state():
    """Inicializa todos los DataFrames en st.session_state."""
    # Código 1: Proveedores, Depósitos, Notas de Débito
    if "data" not in st.session_state:
        st.session_state.data = load_dataframe(DATA_FILE, COLUMNS_DATA, ["Fecha"])
        initial_balance_row_exists = any(st.session_state.data["Proveedor"] == "BALANCE_INICIAL")
        if not initial_balance_row_exists:
            fila_inicial_saldo = {col: None for col in COLUMNS_DATA}
            fila_inicial_saldo.update({
                "Fecha": datetime(1900, 1, 1).date(),
                "Proveedor": "BALANCE_INICIAL",
                "Saldo diario": 0.00,
                "Saldo Acumulado": INITIAL_ACCUMULATED_BALANCE,
                "Monto Deposito": 0.0,
                "Total ($)": 0.0,
                "N": "00"
            })
            st.session_state.data = pd.concat(
                [pd.DataFrame([fila_inicial_saldo]), st.session_state.data], ignore_index=True
            )
        else:
            idx = st.session_state.data[st.session_state.data["Proveedor"] == "BALANCE_INICIAL"].index[0]
            st.session_state.data.loc[idx, "Saldo Acumulado"] = INITIAL_ACCUMULATED_BALANCE
            st.session_state.data.loc[idx, "Saldo diario"] = 0.0
            st.session_state.data.loc[idx, "Monto Deposito"] = 0.0
            st.session_state.data.loc[idx, "Total ($)"] = 0.0
            st.session_state.data.loc[idx, "N"] = "00"
            st.session_state.data.loc[idx, "Fecha"] = datetime(1900, 1, 1).date()

    if "df" not in st.session_state:
        st.session_state.df = load_dataframe(DEPOSITS_FILE, COLUMNS_DEPOSITS, ["Fecha"])
        st.session_state.df["N"] = st.session_state.df["N"].astype(str)

    if "notas" not in st.session_state:
        st.session_state.notas = load_dataframe(DEBIT_NOTES_FILE, COLUMNS_DEBIT_NOTES, ["Fecha"])

    # Código 2: Ventas y Gastos
    if 'ventas_raw_data' not in st.session_state:
        st.session_state.ventas_raw_data = load_dataframe(VENTAS_FILE, COLUMNS_VENTAS, ['fecha'])
    if 'ventas_data' not in st.session_state:
        st.session_state.ventas_data = get_ventas_df_processed()
    if 'gastos_raw_data' not in st.session_state:
        st.session_state.gastos_raw_data = load_dataframe(GASTOS_FILE, COLUMNS_GASTOS, ['fecha'])
    if 'gastos_data' not in st.session_state:
        st.session_state.gastos_data = get_gastos_df_processed()

    # Inicializar flags
    for flag in [
        "deposit_added", "deposit_deleted", "record_added", "record_deleted",
        "data_imported", "debit_note_added", "debit_note_deleted",
        "record_edited", "deposit_edited", "debit_note_edited",
        "venta_added", "venta_deleted", "gasto_added", "gasto_deleted",
        "ventas_edited", "gastos_edited"
    ]:
        if flag not in st.session_state:
            st.session_state[flag] = False

    # Inicializar valores de formulario para ventas y gastos
    for key, value in [
        ('cantidad_venta_val', 0), ('libras_venta_val', 0.0),
        ('descuento_venta_val', 0.0), ('precio_venta_val', 0.0),
        ('pago_venta_val', 0.0), ('cliente_venta_val', CLIENTES[0]),
        ('tipo_venta_val', TIPOS_AVE[0]), ('calculo_gasto_val', 0.0),
        ('descripcion_gasto_val', ''), ('dinero_gasto_val', 0.0),
        ('categoria_gasto_val', CATEGORIAS_GASTO[0])
    ]:
        if key not in st.session_state:
            st.session_state[key] = value

    recalculate_accumulated_balances()

# --- 4. FUNCIONES DE LÓGICA DE NEGOCIO Y CÁLCULOS ---
# Funciones del Código 1
def recalculate_accumulated_balances():
    """Recalcula el Saldo Acumulado para los registros de proveedores."""
    df_data = st.session_state.data.copy()
    df_deposits = st.session_state.df.copy()
    df_notes = st.session_state.notas.copy()

    for df_temp in [df_data, df_deposits, df_notes]:
        if "Fecha" in df_temp.columns:
            df_temp["Fecha"] = pd.to_datetime(df_temp["Fecha"], errors="coerce").dt.date

    df_initial_balance = df_data[df_data["Proveedor"] == "BALANCE_INICIAL"].copy()
    df_data_operaciones = df_data[df_data["Proveedor"] != "BALANCE_INICIAL"].copy()

    numeric_cols_data = [
        "Cantidad", "Peso Salida (kg)", "Peso Entrada (kg)", "Precio Unitario ($)",
        "Monto Deposito", "Total ($)", "Saldo diario", "Saldo Acumulado",
        "Kilos Restantes", "Libras Restantes", "Promedio", "Cantidad de gavetas"
    ]
    for col in numeric_cols_data:
        if col in df_data_operaciones.columns:
            df_data_operaciones[col] = pd.to_numeric(df_data_operaciones[col], errors='coerce').fillna(0)

    if not df_data_operaciones.empty:
        df_data_operaciones["Kilos Restantes"] = df_data_operaciones["Peso Salida (kg)"] - df_data_operaciones["Peso Entrada (kg)"]
        df_data_operaciones["Libras Restantes"] = df_data_operaciones["Kilos Restantes"] * LBS_PER_KG
        df_data_operaciones["Promedio"] = df_data_operaciones.apply(
            lambda row: row["Libras Restantes"] / row["Cantidad"] if row["Cantidad"] != 0 else 0, axis=1
        )
        df_data_operaciones["Total ($)"] = df_data_operaciones["Libras Restantes"] * df_data_operaciones["Precio Unitario ($)"]

    if not df_deposits.empty:
        df_deposits["Monto"] = pd.to_numeric(df_deposits["Monto"], errors='coerce').fillna(0)
        deposits_summary = df_deposits.groupby(["Fecha", "Empresa"])["Monto"].sum().reset_index()
        deposits_summary.rename(columns={"Monto": "Monto Deposito Calculado"}, inplace=True)
        df_data_operaciones["Empresa_key"] = df_data_operaciones["Proveedor"]
        df_data_operaciones = pd.merge(
            df_data_operaciones.drop(columns=["Monto Deposito"], errors='ignore'),
            deposits_summary,
            left_on=["Fecha", "Empresa_key"],
            right_on=["Fecha", "Empresa"],
            how="left"
        )
        df_data_operaciones["Monto Deposito"] = df_data_operaciones["Monto Deposito Calculado"].fillna(0)
        df_data_operaciones.drop(columns=["Monto Deposito Calculado", "Empresa", "Empresa_key"], inplace=True, errors='ignore')
    else:
        df_data_operaciones["Monto Deposito"] = 0.0

    df_data_operaciones["Saldo diario"] = df_data_operaciones["Monto Deposito"] - df_data_operaciones["Total ($)"]

    if not df_notes.empty:
        df_notes["Descuento real"] = pd.to_numeric(df_notes["Descuento real"], errors='coerce').fillna(0)
        notes_by_date = df_notes.groupby("Fecha")["Descuento real"].sum().reset_index()
        notes_by_date.rename(columns={"Descuento real": "NotaDebitoAjuste"}, inplace=True)
        daily_ops_saldo = df_data_operaciones.groupby("Fecha")["Saldo diario"].sum().reset_index()
        full_daily_balances = pd.merge(daily_ops_saldo, notes_by_date, on="Fecha", how="left")
        full_daily_balances["NotaDebitoAjuste"] = full_daily_balances["NotaDebitoAjuste"].fillna(0)
        full_daily_balances["SaldoDiarioAjustado"] = full_daily_balances["Saldo diario"] + full_daily_balances["NotaDebitoAjuste"]
    else:
        full_daily_balances = df_data_operaciones.groupby("Fecha")["Saldo diario"].sum().reset_index()
        full_daily_balances["SaldoDiarioAjustado"] = full_daily_balances["Saldo diario"]

    full_daily_balances = full_daily_balances.sort_values("Fecha")
    full_daily_balances["Saldo Acumulado"] = INITIAL_ACCUMULATED_BALANCE + full_daily_balances["SaldoDiarioAjustado"].cumsum()

    saldo_diario_map = full_daily_balances.set_index("Fecha")["SaldoDiarioAjustado"].to_dict()
    saldo_acumulado_map = full_daily_balances.set_index("Fecha")["Saldo Acumulado"].to_dict()

    if not df_data_operaciones.empty:
        df_data_operaciones["Saldo diario"] = df_data_operaciones["Fecha"].map(saldo_diario_map).fillna(0)
        df_data_operaciones["Saldo Acumulado"] = df_data_operaciones["Fecha"].map(saldo_acumulado_map).fillna(INITIAL_ACCUMULATED_BALANCE)

    if not df_initial_balance.empty:
        df_initial_balance.loc[:, "Saldo Acumulado"] = INITIAL_ACCUMULATED_BALANCE
        df_initial_balance.loc[:, "Saldo diario"] = 0.0
        df_initial_balance.loc[:, "Monto Deposito"] = 0.0
        df_initial_balance.loc[:, "Total ($)"] = 0.0
        df_initial_balance.loc[:, "N"] = "00"
        df_initial_balance.loc[:, "Fecha"] = datetime(1900, 1, 1).date()
        df_data = pd.concat([df_initial_balance, df_data_operaciones], ignore_index=True)
    else:
        df_data = df_data_operaciones

    df_data = df_data[COLUMNS_DATA]
    df_data["N"] = df_data["N"].astype(str)
    df_data = df_data.sort_values(by=["Fecha", "N"], ascending=[True, True]).reset_index(drop=True)
    st.session_state.data = df_data
    save_dataframe(st.session_state.data, DATA_FILE)

def get_next_n(df, current_date):
    """Genera el siguiente número 'N' para un registro."""
    df_filtered = df[df["Proveedor"] != "BALANCE_INICIAL"].copy()
    if not df_filtered.empty:
        df_filtered["N_numeric"] = pd.to_numeric(df_filtered["N"], errors='coerce').fillna(0)
        max_n_global = df_filtered["N_numeric"].max()
        return f"{int(max_n_global) + 1:02}"
    return "01"

def add_deposit_record(fecha_d, empresa, agencia, monto):
    """Agrega un nuevo registro de depósito."""
    df_actual = st.session_state.df.copy()
    df_actual["N"] = df_actual["N"].astype(str)
    if not df_actual.empty:
        valid_n_deposits = df_actual[df_actual["N"].str.isdigit()]["N"].astype(int)
        max_n_deposit = valid_n_deposits.max() if not valid_n_deposits.empty else 0
        numero = f"{max_n_deposit + 1:02}"
    else:
        numero = "01"
    documento = "Deposito" if "Cajero" in agencia else "Transferencia"
    nuevo_registro = {
        "Fecha": fecha_d,
        "Empresa": empresa,
        "Agencia": agencia,
        "Monto": float(monto),
        "Documento": documento,
        "N": numero
    }
    st.session_state.df = pd.concat([df_actual, pd.DataFrame([nuevo_registro])], ignore_index=True)
    if save_dataframe(st.session_state.df, DEPOSITS_FILE):
        st.session_state.deposit_added = True
        st.success("Depósito agregado exitosamente. Recalculando saldos...")
    else:
        st.error("Error al guardar el depósito.")

def delete_deposit_record(index_to_delete):
    """Elimina un registro de depósito."""
    try:
        st.session_state.df = st.session_state.df.drop(index=index_to_delete).reset_index(drop=True)
        if save_dataframe(st.session_state.df, DEPOSITS_FILE):
            st.session_state.deposit_deleted = True
            st.success("Depósito eliminado correctamente. Recalculando saldos...")
        else:
            st.error("Error al eliminar el depósito.")
    except (IndexError, KeyError):
        st.error("Índice de depósito no válido para eliminar.")

def edit_deposit_record(index_to_edit, updated_data):
    """Edita un registro de depósito."""
    try:
        current_df = st.session_state.df.copy()
        if index_to_edit not in current_df.index:
            st.error("El índice de depósito a editar no es válido.")
            return
        for key, value in updated_data.items():
            if key == "Monto":
                current_df.loc[index_to_edit, key] = float(value)
            elif key == "Fecha":
                current_df.loc[index_to_edit, key] = pd.to_datetime(value).date()
            else:
                current_df.loc[index_to_edit, key] = value
        current_df.loc[index_to_edit, "Documento"] = "Deposito" if "Cajero" in str(updated_data.get("Agencia", current_df.loc[index_to_edit, "Agencia"])) else "Transferencia"
        st.session_state.df = current_df
        if save_dataframe(st.session_state.df, DEPOSITS_FILE):
            st.session_state.deposit_edited = True
            st.success("Depósito editado exitosamente. Recalculando saldos...")
        else:
            st.error("Error al guardar los cambios del depósito.")
    except Exception as e:
        st.error(f"Error al editar el depósito: {e}")

def add_supplier_record(fecha, proveedor, cantidad, peso_salida, peso_entrada, tipo_documento, gavetas, precio_unitario):
    """Agrega un nuevo registro de proveedor."""
    df = st.session_state.data.copy()
    if not all(isinstance(val, (int, float)) and val >= 0 for val in [cantidad, peso_salida, peso_entrada, precio_unitario, gavetas]):
        st.error("Los valores numéricos no pueden ser negativos.")
        return False
    if cantidad == 0 and peso_salida == 0 and peso_entrada == 0:
        st.error("Ingresa una Cantidad y/o Pesos válidos (no todos cero).")
        return False
    if peso_entrada > peso_salida:
        st.error("El Peso Entrada (kg) no puede ser mayor que el Peso Salida (kg).")
        return False
    kilos_restantes = peso_salida - peso_entrada
    libras_restantes = kilos_restantes * LBS_PER_KG
    promedio = libras_restantes / cantidad if cantidad != 0 else 0
    total = libras_restantes * precio_unitario
    enumeracion = get_next_n(df, fecha)
    nueva_fila = {
        "N": enumeracion, "Fecha": fecha, "Proveedor": proveedor, "Producto": PRODUCT_NAME,
        "Cantidad": int(cantidad), "Peso Salida (kg)": float(peso_salida), "Peso Entrada (kg)": float(peso_entrada),
        "Tipo Documento": tipo_documento, "Cantidad de gavetas": int(gavetas), "Precio Unitario ($)": float(precio_unitario),
        "Promedio": promedio, "Kilos Restantes": kilos_restantes, "Libras Restantes": libras_restantes,
        "Total ($)": total, "Monto Deposito": 0.0, "Saldo diario": 0.0, "Saldo Acumulado": 0.0
    }
    df_balance = df[df["Proveedor"] == "BALANCE_INICIAL"].copy()
    df_temp = df[df["Proveedor"] != "BALANCE_INICIAL"].copy()
    df_temp = pd.concat([df_temp, pd.DataFrame([nueva_fila])], ignore_index=True)
    st.session_state.data = pd.concat([df_balance, df_temp], ignore_index=True)
    if save_dataframe(st.session_state.data, DATA_FILE):
        st.session_state.record_added = True
        st.success("Registro agregado correctamente. Recalculando saldos...")
        return True
    st.error("Error al guardar el registro.")
    return False

def delete_record(index_to_delete):
    """Elimina un registro de la tabla principal."""
    try:
        if st.session_state.data.loc[index_to_delete, "Proveedor"] == "BALANCE_INICIAL":
            st.error("No se puede eliminar la fila de BALANCE_INICIAL.")
            return
        st.session_state.data = st.session_state.data.drop(index=index_to_delete).reset_index(drop=True)
        if save_dataframe(st.session_state.data, DATA_FILE):
            st.session_state.record_deleted = True
            st.success("Registro eliminado correctamente. Recalculando saldos...")
        else:
            st.error("Error al eliminar el registro.")
    except (IndexError, KeyError):
        st.error("Índice de registro no válido para eliminar.")

def edit_supplier_record(index_to_edit, updated_data):
    """Edita un registro de proveedor."""
    try:
        current_df = st.session_state.data.copy()
        if current_df.loc[index_to_edit, "Proveedor"] == "BALANCE_INICIAL":
            st.error("No se puede editar la fila de BALANCE_INICIAL.")
            return
        for key, value in updated_data.items():
            if key == "Fecha":
                current_df.loc[index_to_edit, key] = pd.to_datetime(value).date()
            elif key in ["Cantidad", "Cantidad de gavetas"]:
                current_df.loc[index_to_edit, key] = int(value)
            elif key in ["Peso Salida (kg)", "Peso Entrada (kg)", "Precio Unitario ($)"]:
                current_df.loc[index_to_edit, key] = float(value)
            else:
                current_df.loc[index_to_edit, key] = value
        peso_salida = current_df.loc[index_to_edit, "Peso Salida (kg)"]
        peso_entrada = current_df.loc[index_to_edit, "Peso Entrada (kg)"]
        cantidad = current_df.loc[index_to_edit, "Cantidad"]
        precio_unitario = current_df.loc[index_to_edit, "Precio Unitario ($)"]
        kilos_restantes = peso_salida - peso_entrada
        libras_restantes = kilos_restantes * LBS_PER_KG
        promedio = libras_restantes / cantidad if cantidad != 0 else 0
        total = libras_restantes * precio_unitario
        current_df.loc[index_to_edit, "Kilos Restantes"] = kilos_restantes
        current_df.loc[index_to_edit, "Libras Restantes"] = libras_restantes
        current_df.loc[index_to_edit, "Promedio"] = promedio
        current_df.loc[index_to_edit, "Total ($)"] = total
        st.session_state.data = current_df
        if save_dataframe(st.session_state.data, DATA_FILE):
            st.session_state.record_edited = True
            st.success("Registro editado exitosamente. Recalculando saldos...")
        else:
            st.error("Error al guardar los cambios del registro.")
    except Exception as e:
        st.error(f"Error al editar el registro: {e}")

def add_debit_note(fecha_nota, descuento, descuento_real):
    """Agrega una nueva nota de débito."""
    df_data = st.session_state.data.copy()
    df_data["Libras Restantes"] = pd.to_numeric(df_data["Libras Restantes"], errors='coerce').fillna(0)
    libras_calculadas = df_data[
        (df_data["Fecha"] == fecha_nota) & (df_data["Proveedor"] != "BALANCE_INICIAL")
    ]["Libras Restantes"].sum()
    descuento_posible = libras_calculadas * descuento
    nueva_nota = {
        "Fecha": fecha_nota,
        "Libras calculadas": libras_calculadas,
        "Descuento": float(descuento),
        "Descuento posible": descuento_posible,
        "Descuento real": float(descuento_real)
    }
    st.session_state.notas = pd.concat([st.session_state.notas, pd.DataFrame([nueva_nota])], ignore_index=True)
    if save_dataframe(st.session_state.notas, DEBIT_NOTES_FILE):
        st.session_state.debit_note_added = True
        st.success("Nota de débito agregada correctamente. Recalculando saldos...")
    else:
        st.error("Error al guardar la nota de débito.")

def delete_debit_note_record(index_to_delete):
    """Elimina una nota de débito."""
    try:
        st.session_state.notas = st.session_state.notas.drop(index=index_to_delete).reset_index(drop=True)
        if save_dataframe(st.session_state.notas, DEBIT_NOTES_FILE):
            st.session_state.debit_note_deleted = True
            st.success("Nota de débito eliminada correctamente. Recalculando saldos...")
        else:
            st.error("Error al eliminar la nota de débito.")
    except (IndexError, KeyError):
        st.error("Índice de nota de débito no válido para eliminar.")

def edit_debit_note_record(index_to_edit, updated_data):
    """Edita una nota de débito."""
    try:
        current_df = st.session_state.notas.copy()
        if index_to_edit not in current_df.index:
            st.error("El índice de nota de débito a editar no es válido.")
            return
        for key, value in updated_data.items():
            if key == "Fecha":
                current_df.loc[index_to_edit, key] = pd.to_datetime(value).date()
            elif key in ["Descuento", "Descuento real"]:
                current_df.loc[index_to_edit, key] = float(value)
            else:
                current_df.loc[index_to_edit, key] = value
        fecha_nota_actual = current_df.loc[index_to_edit, "Fecha"]
        descuento_actual = current_df.loc[index_to_edit, "Descuento"]
        df_data_for_calc = st.session_state.data.copy()
        df_data_for_calc["Libras Restantes"] = pd.to_numeric(df_data_for_calc["Libras Restantes"], errors='coerce').fillna(0)
        libras_calculadas_recalc = df_data_for_calc[
            (df_data_for_calc["Fecha"] == fecha_nota_actual) & (df_data_for_calc["Proveedor"] != "BALANCE_INICIAL")
        ]["Libras Restantes"].sum()
        current_df.loc[index_to_edit, "Libras calculadas"] = libras_calculadas_recalc
        current_df.loc[index_to_edit, "Descuento posible"] = libras_calculadas_recalc * descuento_actual
        st.session_state.notas = current_df
        if save_dataframe(st.session_state.notas, DEBIT_NOTES_FILE):
            st.session_state.debit_note_edited = True
            st.success("Nota de débito editada exitosamente. Recalculando saldos...")
        else:
            st.error("Error al guardar los cambios de la nota de débito.")
    except Exception as e:
        st.error(f"Error al editar la nota de débito: {e}")

def import_excel_data(archivo_excel):
    """Importa datos desde un archivo Excel."""
    try:
        xls = pd.ExcelFile(archivo_excel)
        sheet_names = xls.sheet_names

        # Proveedores
        df_proveedores_importado = pd.DataFrame(columns=COLUMNS_DATA)
        if "registro de proveedores" in sheet_names:
            df_proveedores_importado = pd.read_excel(xls, sheet_name="registro de proveedores")
            columnas_requeridas_proveedores = [
                "Fecha", "Proveedor", "Cantidad", "Peso Salida (kg)", "Peso Entrada (kg)",
                "Tipo Documento", "Cantidad de gavetas", "Precio Unitario ($)"
            ]
            if not all(col in df_proveedores_importado.columns for col in columnas_requeridas_proveedores):
                st.warning(f"La hoja 'registro de proveedores' no contiene todas las columnas requeridas.")
            else:
                df_proveedores_importado["Fecha"] = pd.to_datetime(df_proveedores_importado["Fecha"], errors="coerce").dt.date
                df_proveedores_importado.dropna(subset=["Fecha"], inplace=True)
                for col in ["Cantidad", "Peso Salida (kg)", "Peso Entrada (kg)", "Precio Unitario ($)", "Cantidad de gavetas"]:
                    df_proveedores_importado[col] = pd.to_numeric(df_proveedores_importado[col], errors='coerce').fillna(0)
                df_proveedores_importado["Kilos Restantes"] = df_proveedores_importado["Peso Salida (kg)"] - df_proveedores_importado["Peso Entrada (kg)"]
                df_proveedores_importado["Libras Restantes"] = df_proveedores_importado["Kilos Restantes"] * LBS_PER_KG
                df_proveedores_importado["Promedio"] = df_proveedores_importado.apply(
                    lambda row: row["Libras Restantes"] / row["Cantidad"] if row["Cantidad"] != 0 else 0, axis=1
                )
                df_proveedores_importado["Total ($)"] = df_proveedores_importado["Libras Restantes"] * df_proveedores_importado["Precio Unitario ($)"]
                current_ops_data = st.session_state.data[st.session_state.data["Proveedor"] != "BALANCE_INICIAL"].copy()
                max_n_existing_proveedores = 0
                if not current_ops_data.empty:
                    max_n_existing_proveedores = current_ops_data["N"].apply(lambda x: int(x) if isinstance(x, str) and x.isdigit() else 0).max()
                new_n_counter_proveedores = max_n_existing_proveedores + 1
                df_proveedores_importado["N"] = [f"{new_n_counter_proveedores + i:02}" for i in range(len(df_proveedores_importado))]
                df_proveedores_importado["Monto Deposito"] = 0.0
                df_proveedores_importado["Saldo diario"] = 0.0
                df_proveedores_importado["Saldo Acumulado"] = 0.0
                df_proveedores_importado["Producto"] = PRODUCT_NAME
                df_proveedores_importado = df_proveedores_importado[COLUMNS_DATA]

        # Depósitos
        df_depositos_importado = pd.DataFrame(columns=COLUMNS_DEPOSITS)
        if "registro de depositos" in sheet_names:
            df_depositos_importado = pd.read_excel(xls, sheet_name="registro de depositos")
            columnas_requeridas_depositos = ["Fecha", "Empresa", "Agencia", "Monto"]
            if not all(col in df_depositos_importado.columns for col in columnas_requeridas_depositos):
                st.warning(f"La hoja 'registro de depositos' no contiene todas las columnas requeridas.")
            else:
                df_depositos_importado["Fecha"] = pd.to_datetime(df_depositos_importado["Fecha"], errors="coerce").dt.date
                df_depositos_importado.dropna(subset=["Fecha"], inplace=True)
                df_depositos_importado["Monto"] = pd.to_numeric(df_depositos_importado["Monto"], errors='coerce').fillna(0)
                current_deposits_data = st.session_state.df.copy()
                max_n_existing_deposits = 0
                if not current_deposits_data.empty:
                    valid_n_deposits = current_deposits_data[current_deposits_data["N"].str.isdigit()]["N"].astype(int)
                    max_n_existing_deposits = valid_n_deposits.max() if not valid_n_deposits.empty else 0
                new_n_counter_deposits = max_n_existing_deposits + 1
                df_depositos_importado["N"] = [f"{new_n_counter_deposits + i:02}" for i in range(len(df_depositos_importado))]
                df_depositos_importado["Documento"] = df_depositos_importado["Agencia"].apply(
                    lambda x: "Deposito" if "Cajero" in str(x) else "Transferencia"
                )
                df_depositos_importado = df_depositos_importado[COLUMNS_DEPOSITS]

        # Notas de Débito
        df_notas_debito_importado = pd.DataFrame(columns=COLUMNS_DEBIT_NOTES)
        if "registro de notas de debito" in sheet_names:
            df_notas_debito_importado = pd.read_excel(xls, sheet_name="registro de notas de debito")
            columnas_requeridas_notas = ["Fecha", "Descuento", "Descuento real"]
            if not all(col in df_notas_debito_importado.columns for col in columnas_requeridas_notas):
                st.warning(f"La hoja 'registro de notas de debito' no contiene todas las columnas requeridas.")
            else:
                df_notas_debito_importado["Fecha"] = pd.to_datetime(df_notas_debito_importado["Fecha"], errors="coerce").dt.date
                df_notas_debito_importado.dropna(subset=["Fecha"], inplace=True)
                df_notas_debito_importado["Descuento"] = pd.to_numeric(df_notas_debito_importado["Descuento"], errors='coerce').fillna(0)
                df_notas_debito_importado["Descuento real"] = pd.to_numeric(df_notas_debito_importado["Descuento real"], errors='coerce').fillna(0)
                if not df_notas_debito_importado.empty and not st.session_state.data.empty:
                    df_data_for_calc_notes = st.session_state.data.copy()
                    df_data_for_calc_notes["Libras Restantes"] = pd.to_numeric(df_data_for_calc_notes["Libras Restantes"], errors='coerce').fillna(0)
                    df_notas_debito_importado["Libras calculadas"] = df_notas_debito_importado["Fecha"].apply(
                        lambda f: df_data_for_calc_notes[
                            (df_data_for_calc_notes["Fecha"] == f) & (df_data_for_calc_notes["Proveedor"] != "BALANCE_INICIAL")
                        ]["Libras Restantes"].sum()
                    )
                    df_notas_debito_importado["Descuento posible"] = df_notas_debito_importado["Libras calculadas"] * df_notas_debito_importado["Descuento"]
                else:
                    df_notas_debito_importado["Libras calculadas"] = 0.0
                    df_notas_debito_importado["Descuento posible"] = 0.0
                df_notas_debito_importado = df_notas_debito_importado[COLUMNS_DEBIT_NOTES]

        # Ventas
        df_ventas_importado = pd.DataFrame(columns=COLUMNS_VENTAS)
        if "ventas" in sheet_names:
            df_ventas_importado = pd.read_excel(xls, sheet_name="ventas")
            expected_cols_ventas = COLUMNS_VENTAS
            df_ventas_importado.columns = df_ventas_importado.columns.str.lower().str.replace(' ', '_')
            if not all(col in df_ventas_importado.columns for col in expected_cols_ventas):
                st.warning(f"La hoja 'ventas' no contiene todas las columnas requeridas: {', '.join(expected_cols_ventas)}.")
            else:
                for col in ['cantidad']:
                    df_ventas_importado[col] = pd.to_numeric(df_ventas_importado[col], errors='coerce').fillna(0).astype(int)
                for col in ['libras', 'descuento', 'libras_netas', 'precio', 'total_a_cobrar', 'pago_cliente', 'saldo']:
                    df_ventas_importado[col] = pd.to_numeric(df_ventas_importado[col], errors='coerce').fillna(0.0).round(2)
                df_ventas_importado['fecha'] = pd.to_datetime(df_ventas_importado['fecha'], errors='coerce').dt.date
                df_ventas_importado.dropna(subset=['fecha'], inplace=True)
                df_ventas_importado = df_ventas_importado[expected_cols_ventas]

        # Gastos
        df_gastos_importado = pd.DataFrame(columns=COLUMNS_GASTOS)
        if "gastos" in sheet_names:
            df_gastos_importado = pd.read_excel(xls, sheet_name="gastos")
            expected_cols_gastos = COLUMNS_GASTOS
            df_gastos_importado.columns = df_gastos_importado.columns.str.lower().str.replace(' ', '_')
            if not all(col in df_gastos_importado.columns for col in expected_cols_gastos):
                st.warning(f"La hoja 'gastos' no contiene todas las columnas requeridas: {', '.join(expected_cols_gastos)}.")
            else:
                for col in ['calculo', 'dinero']:
                    df_gastos_importado[col] = pd.to_numeric(df_gastos_importado[col], errors='coerce').fillna(0.0).round(2)
                df_gastos_importado['fecha'] = pd.to_datetime(df_gastos_importado['fecha'], errors='coerce').dt.date
                df_gastos_importado.dropna(subset=['fecha'], inplace=True)
                df_gastos_importado = df_gastos_importado[expected_cols_gastos]

        if st.button("Cargar datos a registros desde Excel"):
            if not df_proveedores_importado.empty:
                df_balance = st.session_state.data[st.session_state.data["Proveedor"] == "BALANCE_INICIAL"].copy()
                df_temp = st.session_state.data[st.session_state.data["Proveedor"] != "BALANCE_INICIAL"].copy()
                st.session_state.data = pd.concat([df_balance, df_temp, df_proveedores_importado], ignore_index=True)
                save_dataframe(st.session_state.data, DATA_FILE)
                st.session_state.data_imported = True
            if not df_depositos_importado.empty:
                st.session_state.df = pd.concat([st.session_state.df, df_depositos_importado], ignore_index=True)
                st.session_state.df["N"] = st.session_state.df["N"].astype(str)
                save_dataframe(st.session_state.df, DEPOSITS_FILE)
                st.session_state.data_imported = True
            if not df_notas_debito_importado.empty:
                st.session_state.notas = pd.concat([st.session_state.notas, df_notas_debito_importado], ignore_index=True)
                save_dataframe(st.session_state.notas, DEBIT_NOTES_FILE)
                st.session_state.data_imported = True
            if not df_ventas_importado.empty:
                st.session_state.ventas_raw_data = pd.concat([st.session_state.ventas_raw_data, df_ventas_importado], ignore_index=True)
                st.session_state.ventas_raw_data.drop_duplicates(subset=['fecha', 'cliente', 'tipo', 'cantidad', 'libras', 'precio'], keep='first', inplace=True)
                save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE)
                st.session_state.data_imported = True
                st.session_state.ventas_data = get_ventas_df_processed()
            if not df_gastos_importado.empty:
                st.session_state.gastos_raw_data = pd.concat([st.session_state.gastos_raw_data, df_gastos_importado], ignore_index=True)
                st.session_state.gastos_raw_data.drop_duplicates(subset=['fecha', 'gasto', 'dinero'], keep='first', inplace=True)
                save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE)
                st.session_state.data_imported = True
                st.session_state.gastos_data = get_gastos_df_processed()
            if st.session_state.data_imported:
                st.success("Datos importados correctamente. Recalculando saldos...")
            else:
                st.info("No se importaron datos válidos de ninguna hoja.")
    except Exception as e:
        st.error(f"Error al cargar el archivo Excel: {e}")

# Funciones del Código 2
def get_ventas_df_processed():
    """Procesa el DataFrame de ventas para visualización."""
    df = st.session_state.ventas_raw_data.copy()
    if not df.empty:
        if 'fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['fecha']).dt.date
        else:
            df['Fecha'] = date.today()
            st.warning("Columna 'fecha' no encontrada en ventas_raw_data. Usando fecha actual.")
        df = df.rename(columns={
            'fecha': 'Fecha DB', 'cliente': 'Cliente', 'tipo': 'Tipo', 'cantidad': 'Cantidad',
            'libras': 'Libras', 'descuento': 'Descuento', 'libras_netas': 'Libras_netas',
            'precio': 'Precio', 'total_a_cobrar': 'Total_a_cobrar', 'pago_cliente': 'Pago_Cliente',
            'saldo': 'Saldo'
        })
        df = df.sort_values(by=['Fecha', 'Cliente'], ascending=[False, True])
    return df

def get_gastos_df_processed():
    """Procesa el DataFrame de gastos para visualización."""
    df = st.session_state.gastos_raw_data.copy()
    if not df.empty:
        if 'fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['fecha']).dt.date
        else:
            df['Fecha'] = date.today()
            st.warning("Columna 'fecha' no encontrada en gastos_raw_data. Usando fecha actual.")
        df = df.rename(columns={
            'fecha': 'Fecha DB', 'calculo': 'Calculo', 'descripcion': 'Descripcion',
            'gasto': 'Gasto', 'dinero': 'Dinero'
        })
        df = df.sort_values(by='Fecha', ascending=False)
    return df

def guardar_venta(venta_data):
    """Guarda una nueva venta."""
    nueva_venta_df = pd.DataFrame([venta_data])
    st.session_state.ventas_raw_data = pd.concat([nueva_venta_df, st.session_state.ventas_raw_data], ignore_index=True)
    if save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE):
        st.session_state.venta_added = True
        st.session_state.ventas_data = get_ventas_df_processed()
        return True
    return False

def guardar_gasto(gasto_data):
    """Guarda un nuevo gasto."""
    nuevo_gasto_df = pd.DataFrame([gasto_data])
    st.session_state.gastos_raw_data = pd.concat([nuevo_gasto_df, st.session_state.gastos_raw_data], ignore_index=True)
    if save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE):
        st.session_state.gasto_added = True
        st.session_state.gastos_data = get_gastos_df_processed()
        return True
    return False

def limpiar_ventas():
    """Elimina todas las ventas."""
    st.session_state.ventas_raw_data = pd.DataFrame(columns=COLUMNS_VENTAS)
    if save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE):
        if os.path.exists(VENTAS_FILE):
            os.remove(VENTAS_FILE)
        st.session_state.ventas_data = get_ventas_df_processed()
        return True
    return False

def limpiar_gastos():
    """Elimina todos los gastos."""
    st.session_state.gastos_raw_data = pd.DataFrame(columns=COLUMNS_GASTOS)
    if save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE):
        if os.path.exists(GASTOS_FILE):
            os.remove(GASTOS_FILE)
        st.session_state.gastos_data = get_gastos_df_processed()
        return True
    return False

def actualizar_venta(index, updated_data):
    """Actualiza una venta existente."""
    try:
        for col, val in updated_data.items():
            if col == 'fecha':
                st.session_state.ventas_raw_data.loc[index, col] = pd.to_datetime(val).date()
            else:
                st.session_state.ventas_raw_data.loc[index, col] = val
        libras = st.session_state.ventas_raw_data.loc[index, 'libras']
        descuento = st.session_state.ventas_raw_data.loc[index, 'descuento']
        precio = st.session_state.ventas_raw_data.loc[index, 'precio']
        pago_cliente = st.session_state.ventas_raw_data.loc[index, 'pago_cliente']
        st.session_state.ventas_raw_data.loc[index, 'libras_netas'] = calcular_libras_netas(libras, descuento)
        st.session_state.ventas_raw_data.loc[index, 'total_a_cobrar'] = calcular_total_cobrar(
            st.session_state.ventas_raw_data.loc[index, 'libras_netas'], precio
        )
        st.session_state.ventas_raw_data.loc[index, 'saldo'] = calcular_saldo(
            st.session_state.ventas_raw_data.loc[index, 'total_a_cobrar'], pago_cliente
        )
        if save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE):
            st.session_state.ventas_edited = True
            st.session_state.ventas_data = get_ventas_df_processed()
            return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar la venta: {e}")
        return False

def eliminar_ventas_seleccionadas(indices):
    """Elimina ventas seleccionadas."""
    try:
        st.session_state.ventas_raw_data = st.session_state.ventas_raw_data.drop(indices).reset_index(drop=True)
        if save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE):
            st.session_state.venta_deleted = True
            st.session_state.ventas_data = get_ventas_df_processed()
            return True
        return False
    except Exception as e:
        st.error(f"Error al eliminar ventas: {e}")
        return False

def actualizar_gasto(index, updated_data):
    """Actualiza un gasto existente."""
    try:
        for col, val in updated_data.items():
            if col == 'fecha':
                st.session_state.gastos_raw_data.loc[index, col] = pd.to_datetime(val).date()
            else:
                st.session_state.gastos_raw_data.loc[index, col] = val
        if save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE):
            st.session_state.gastos_edited = True
            st.session_state.gastos_data = get_gastos_df_processed()
            return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar el gasto: {e}")
        return False

def eliminar_gastos_seleccionados(indices):
    """Elimina gastos seleccionados."""
    try:
        st.session_state.gastos_raw_data = st.session_state.gastos_raw_data.drop(indices).reset_index(drop=True)
        if save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE):
            st.session_state.gasto_deleted = True
            st.session_state.gastos_data = get_gastos_df_processed()
            return True
        return False
    except Exception as e:
        st.error(f"Error al eliminar gastos: {e}")
        return False

def formatear_moneda(valor):
    """Formatea un valor numérico como moneda."""
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
    df_temp = ventas_df.copy()
    if 'Fecha' in df_temp.columns:
        df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha'])
    else:
        df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha DB'])
    alertas = []
    for cliente in df_temp['Cliente'].unique():
        cliente_ventas = df_temp[df_temp['Cliente'] == cliente].copy()
        cliente_ventas = cliente_ventas.sort_values('Fecha')
        cliente_ventas['Saldo_num'] = cliente_ventas['Saldo'].apply(
            lambda x: float(str(x).replace('$', '').replace(',', '')) if isinstance(x, (str, float, int)) else x
        )
        saldo_total = cliente_ventas['Saldo_num'].sum()
        debe_mas_10 = saldo_total > 10
        dias_consecutivos = 0
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

# --- 5. FUNCIONES DE INTERFAZ DE USUARIO (UI) ---
def render_deposit_registration_form():
    """Renderiza el formulario de registro de depósitos."""
    st.sidebar.header("📝 Registro de Depósitos")
    with st.sidebar.form("registro_deposito_form", clear_on_submit=True):
        fecha_d = st.date_input("Fecha del registro", value=datetime.today().date(), key="fecha_d_input_sidebar")
        empresa = st.selectbox("Empresa (Proveedor)", PROVEEDORES, key="empresa_select_sidebar")
        agencia = st.selectbox("Agencia", AGENCIAS, key="agencia_select_sidebar")
        monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f", key="monto_input_sidebar")
        submit_d = st.form_submit_button("➕ Agregar Depósito")
        if submit_d:
            if monto <= 0:
                st.error("El monto del depósito debe ser mayor que cero.")
            else:
                add_deposit_record(fecha_d, empresa, agencia, monto)

def render_delete_deposit_section():
    """Renderiza la sección para eliminar depósitos."""
    st.sidebar.subheader("🗑️ Eliminar Depósito")
    if not st.session_state.df.empty:
        df_display_deposits = st.session_state.df.copy()
        df_display_deposits["Display"] = df_display_deposits.apply(
            lambda row: f"{row.name} - {row['Fecha']} - {row['Empresa']} - ${row['Monto']:.2f}", axis=1
        )
        if not df_display_deposits["Display"].empty:
            deposito_seleccionado_info = st.sidebar.selectbox(
                "Selecciona un depósito a eliminar", df_display_deposits["Display"], key="delete_deposit_select"
            )
            index_to_delete = int(deposito_seleccionado_info.split(' - ')[0]) if deposito_seleccionado_info else None
            if st.sidebar.button("🗑️ Eliminar depósito seleccionado", key="delete_deposit_button"):
                if index_to_delete is not None and st.sidebar.checkbox("✅ Confirmar eliminación del depósito"):
                    delete_deposit_record(index_to_delete)
                else:
                    st.sidebar.warning("Por favor, marca la casilla para confirmar la eliminación.")
        else:
            st.sidebar.info("No hay depósitos para eliminar.")
    else:
        st.sidebar.info("No hay depósitos para eliminar.")

def render_edit_deposit_section():
    """Renderiza la sección para editar depósitos."""
    st.sidebar.subheader("✏️ Editar Depósito")
    if not st.session_state.df.empty:
        df_display_deposits = st.session_state.df.copy()
        df_display_deposits["Display"] = df_display_deposits.apply(
            lambda row: f"{row.name} - {row['Fecha']} - {row['Empresa']} - ${row['Monto']:.2f}", axis=1
        )
        if not df_display_deposits["Display"].empty:
            deposito_seleccionado_info = st.sidebar.selectbox(
                "Selecciona un depósito para editar", df_display_deposits["Display"], key="edit_deposit_select"
            )
            index_to_edit = int(deposito_seleccionado_info.split(' - ')[0]) if deposito_seleccionado_info else None
            if index_to_edit is not None and index_to_edit in st.session_state.df.index:
                deposit_to_edit = st.session_state.df.loc[index_to_edit].to_dict()
                with st.sidebar.form(f"edit_deposit_form_{index_to_edit}", clear_on_submit=False):
                    st.write(f"Editando depósito: **ID {index_to_edit}**")
                    default_empresa_idx = PROVEEDORES.index(deposit_to_edit["Empresa"]) if deposit_to_edit["Empresa"] in PROVEEDORES else 0
                    default_agencia_idx = AGENCIAS.index(deposit_to_edit["Agencia"]) if deposit_to_edit["Agencia"] in AGENCIAS else 0
                    edited_fecha = st.date_input("Fecha", value=deposit_to_edit["Fecha"], key=f"edit_fecha_d_{index_to_edit}")
                    edited_empresa = st.selectbox("Empresa (Proveedor)", PROVEEDORES, index=default_empresa_idx, key=f"edit_empresa_{index_to_edit}")
                    edited_agencia = st.selectbox("Agencia", AGENCIAS, index=default_agencia_idx, key=f"edit_agencia_{index_to_edit}")
                    edited_monto = st.number_input("Monto ($)", value=float(deposit_to_edit["Monto"]), min_value=0.0, format="%.2f", key=f"edit_monto_{index_to_edit}")
                    submit_edit_deposit = st.form_submit_button("💾 Guardar Cambios del Depósito")
                    if submit_edit_deposit and edited_monto > 0:
                        updated_data = {
                            "Fecha": edited_fecha, "Empresa": edited_empresa,
                            "Agencia": edited_agencia, "Monto": edited_monto
                        }
                        edit_deposit_record(index_to_edit, updated_data)
                    elif submit_edit_deposit:
                        st.error("El monto del depósito debe ser mayor que cero.")
            else:
                st.sidebar.info("Selecciona un depósito para ver sus detalles de edición.")
        else:
            st.sidebar.info("No hay depósitos para editar.")
    else:
        st.sidebar.info("No hay depósitos para editar.")

def render_import_excel_section():
    """Renderiza la sección para importar datos desde Excel."""
    st.subheader("📁 Importar datos desde Excel")
    st.info("Asegúrate de que tu archivo Excel tenga las siguientes hojas y columnas (nombres exactos):")
    st.markdown("- **Hoja 'registro de proveedores':** `Fecha`, `Proveedor`, `Cantidad`, `Peso Salida (kg)`, `Peso Entrada (kg)`, `Tipo Documento`, `Cantidad de gavetas`, `Precio Unitario ($)`")
    st.markdown("- **Hoja 'registro de depositos':** `Fecha`, `Empresa`, `Agencia`, `Monto`")
    st.markdown("- **Hoja 'registro de notas de debito':** `Fecha`, `Descuento`, `Descuento real`")
    st.markdown("- **Hoja 'ventas':** `fecha`, `cliente`, `tipo`, `cantidad`, `libras`, `descuento`, `libras_netas`, `precio`, `total_a_cobrar`, `pago_cliente`, `saldo`")
    st.markdown("- **Hoja 'gastos':** `fecha`, `calculo`, `descripcion`, `gasto`, `dinero`")
    archivo_excel = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"], key="excel_uploader")
    if archivo_excel:
        import_excel_data(archivo_excel)

def render_supplier_registration_form():
    """Renderiza el formulario de registro de proveedores."""
    st.subheader("➕ Registro de Proveedores")
    with st.form("formulario_registro_proveedor", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.today().date(), key="fecha_input_form")
            proveedor = st.selectbox("Proveedor", PROVEEDORES, key="proveedor_select_form")
        with col2:
            cantidad = st.number_input("Cantidad", min_value=0, step=1, key="cantidad_input_form")
            peso_salida = st.number_input("Peso Salida (kg)", min_value=0.0, step=0.1, format="%.2f", key="peso_salida_input_form")
        with col3:
            peso_entrada = st.number_input("Peso Entrada (kg)", min_value=0.0, step=0.1, format="%.2f", key="peso_entrada_input_form")
            documento = st.selectbox("Tipo Documento", TIPOS_DOCUMENTO, key="documento_select_form")
        with col4:
            gavetas = st.number_input("Cantidad de gavetas", min_value=0, step=1, key="gavetas_input_form")
            precio_unitario = st.number_input("Precio Unitario ($)", min_value=0.0, step=0.01, format="%.2f", key="precio_unitario_input_form")
        enviar = st.form_submit_button("➕ Agregar Registro")
        if enviar:
            add_supplier_record(fecha, proveedor, cantidad, peso_salida, peso_entrada, documento, gavetas, precio_unitario)

def render_debit_note_form():
    """Renderiza el formulario para agregar notas de débito."""
    st.subheader("📝 Registro de Nota de Débito")
    with st.form("nota_debito_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_nota = st.date_input("Fecha de Nota", value=datetime.today().date(), key="fecha_nota_input_form")
        with col2:
            descuento = st.number_input("Descuento (%) (ej. 0.05 para 5%)", min_value=0.0, max_value=1.0, step=0.01, format="%.2f", value=0.0, key="descuento_input_form")
        with col3:
            descuento_real = st.number_input("Descuento Real ($)", min_value=0.0, step=0.01, format="%.2f", value=0.0, key="descuento_real_input_form")
        agregar_nota = st.form_submit_button("➕ Agregar Nota de Débito")
        if agregar_nota and (descuento_real > 0 or descuento > 0):
            add_debit_note(fecha_nota, descuento, descuento_real)
        elif agregar_nota:
            st.error("Ingresa un valor para Descuento (%) o Descuento Real ($) mayor que cero.")

def render_delete_debit_note_section():
    """Renderiza la sección para eliminar notas de débito."""
    st.subheader("🗑️ Eliminar Nota de Débito")
    if not st.session_state.notas.empty:
        df_display_notes = st.session_state.notas.copy()
        df_display_notes["Display"] = df_display_notes.apply(
            lambda row: f"{row.name} - {row['Fecha']} - Descuento real: ${row['Descuento real']:.2f}", axis=1
        )
        if not df_display_notes["Display"].empty:
            nota_seleccionada_info = st.selectbox(
                "Selecciona una nota de débito para eliminar", df_display_notes["Display"], key="delete_debit_note_select"
            )
            index_to_delete = int(nota_seleccionada_info.split(' - ')[0]) if nota_seleccionada_info else None
            if st.button("🗑️ Eliminar Nota de Débito seleccionada", key="delete_debit_note_button"):
                if index_to_delete is not None and st.checkbox("✅ Confirmar eliminación de la nota de débito"):
                    delete_debit_note_record(index_to_delete)
                else:
                    st.warning("Por favor, marca la casilla para confirmar la eliminación.")
        else:
            st.info("No hay notas de débito para eliminar.")
    else:
        st.info("No hay notas de débito para eliminar.")

def render_edit_debit_note_section():
    """Renderiza la sección para editar notas de débito."""
    st.subheader("✏️ Editar Nota de Débito")
    if not st.session_state.notas.empty:
        df_display_notes = st.session_state.notas.copy()
        df_display_notes["Display"] = df_display_notes.apply(
            lambda row: f"{row.name} - {row['Fecha']} - Descuento real: ${row['Descuento real']:.2f}", axis=1
        )
        if not df_display_notes["Display"].empty:
            nota_seleccionada_info = st.selectbox(
                "Selecciona una nota de débito para editar", df_display_notes["Display"], key="edit_debit_note_select"
            )
            index_to_edit = int(nota_seleccionada_info.split(' - ')[0]) if nota_seleccionada_info else None
            if index_to_edit is not None and index_to_edit in st.session_state.notas.index:
                note_to_edit = st.session_state.notas.loc[index_to_edit].to_dict()
                with st.form(f"edit_debit_note_form_{index_to_edit}", clear_on_submit=False):
                    st.write(f"Editando nota de débito: **ID {index_to_edit}**")
                    edited_fecha_nota = st.date_input("Fecha de Nota", value=note_to_edit["Fecha"], key=f"edit_fecha_nota_{index_to_edit}")
                    edited_descuento = st.number_input("Descuento (%)", value=float(note_to_edit["Descuento"]), min_value=0.0, max_value=1.0, step=0.01, format="%.2f", key=f"edit_descuento_{index_to_edit}")
                    edited_descuento_real = st.number_input("Descuento Real ($)", value=float(note_to_edit["Descuento real"]), min_value=0.0, step=0.01, format="%.2f", key=f"edit_descuento_real_{index_to_edit}")
                    submit_edit_note = st.form_submit_button("💾 Guardar Cambios de Nota de Débito")
                    if submit_edit_note and (edited_descuento_real > 0 or edited_descuento > 0):
                        updated_data = {
                            "Fecha": edited_fecha_nota, "Descuento": edited_descuento,
                            "Descuento real": edited_descuento_real
                        }
                        edit_debit_note_record(index_to_edit, updated_data)
                    elif submit_edit_note:
                        st.error("Ingresa un valor para Descuento (%) o Descuento Real ($) mayor que cero.")
            else:
                st.info("Selecciona una nota de débito para ver sus detalles de edición.")
        else:
            st.info("No hay notas de débito para editar.")
    else:
        st.info("No hay notas de débito para editar.")

def display_formatted_dataframe(df_source, title, columns_to_format=None, key_suffix="", editable_cols=None):
    """Muestra un DataFrame con formato y capacidad de edición."""
    st.subheader(title)
    df_display = df_source.copy()
    if columns_to_format:
        for col in columns_to_format:
            if col in df_display.columns:
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
                df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
    if "Fecha" in df_display.columns:
        df_display["Fecha"] = df_display["Fecha"].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "")
    column_config = {}
    if editable_cols:
        for col_name, col_type in editable_cols.items():
            if col_type == "text":
                column_config[col_name] = st.column_config.TextColumn(col_name)
            elif col_type == "number":
                column_config[col_name] = st.column_config.NumberColumn(col_name, format="%.2f")
            elif col_type == "date":
                column_config[col_name] = st.column_config.DateColumn(col_name, format="YYYY-MM-DD")
            elif col_type == "selectbox_proveedores":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=PROVEEDORES)
            elif col_type == "selectbox_documento":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=TIPOS_DOCUMENTO)
            elif col_type == "selectbox_agencias":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=AGENCIAS)
            elif col_type == "selectbox_clientes":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=CLIENTES)
            elif col_type == "selectbox_tipos_ave":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=TIPOS_AVE)
            elif col_type == "selectbox_categorias_gasto":
                column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=CATEGORIAS_GASTO)
            elif col_type == "number_int":
                column_config[col_name] = st.column_config.NumberColumn(col_name, format="%d", step=1)
    edited_df = st.dataframe(
        df_display, use_container_width=True, key=f"editable_df_{key_suffix}", hide_index=False, column_config=column_config
    )
    if f"editable_df_{key_suffix}" in st.session_state and st.session_state[f"editable_df_{key_suffix}"]["edited_rows"]:
        st.info("¡Se han detectado cambios en la tabla! Presiona 'Guardar Cambios' para aplicar.")
        if st.button(f"💾 Guardar Cambios en {title}", key=f"save_changes_{key_suffix}"):
            try:
                df_updated_rows = st.session_state[f"editable_df_{key_suffix}"]["edited_rows"]
                original_df_to_update = df_source.copy()
                for idx_str, changes in df_updated_rows.items():
                    idx = int(idx_str)
                    if title == "Tabla de Registros" and original_df_to_update.loc[idx, "Proveedor"] == "BALANCE_INICIAL":
                        st.warning(f"No se pueden editar las propiedades de la fila de BALANCE_INICIAL (ID: {idx}).")
                        continue
                    for col, value in changes.items():
                        original_type = df_source[col].dtype
                        if pd.api.types.is_datetime64_any_dtype(original_type) or isinstance(df_source.loc[idx, col], (date, datetime)):
                            try:
                                original_df_to_update.loc[idx, col] = pd.to_datetime(value).date()
                            except (ValueError, TypeError):
                                st.warning(f"Formato de fecha inválido para '{col}' en la fila {idx}.")
                                original_df_to_update.loc[idx, col] = df_source.loc[idx, col]
                        elif pd.api.types.is_numeric_dtype(original_type):
                            try:
                                if editable_cols and editable_cols.get(col) == "number_int":
                                    original_df_to_update.loc[idx, col] = int(value)
                                else:
                                    original_df_to_update.loc[idx, col] = float(value)
                            except (ValueError, TypeError):
                                st.warning(f"Valor numérico inválido para '{col}' en la fila {idx}.")
                                original_df_to_update.loc[idx, col] = df_source.loc[idx, col]
                        else:
                            original_df_to_update.loc[idx, col] = value
                if title == "Tabla de Registros":
                    st.session_state.data = original_df_to_update
                    if save_dataframe(st.session_state.data, DATA_FILE):
                        st.session_state.record_edited = True
                        st.success("Cambios en Tabla de Registros guardados exitosamente.")
                elif title == "Depósitos Registrados":
                    st.session_state.df = original_df_to_update
                    if save_dataframe(st.session_state.df, DEPOSITS_FILE):
                        st.session_state.deposit_edited = True
                        st.success("Cambios en Depósitos Registrados guardados exitosamente.")
                elif title == "Tabla de Notas de Débito":
                    st.session_state.notas = original_df_to_update
                    if save_dataframe(st.session_state.notas, DEBIT_NOTES_FILE):
                        st.session_state.debit_note_edited = True
                        st.success("Cambios en Tabla de Notas de Débito guardados exitosamente.")
                elif title == "Historial de Ventas":
                    st.session_state.ventas_raw_data = original_df_to_update
                    if save_dataframe(st.session_state.ventas_raw_data, VENTAS_FILE):
                        st.session_state.ventas_edited = True
                        st.session_state.ventas_data = get_ventas_df_processed()
                        st.success("Cambios en Historial de Ventas guardados exitosamente.")
                elif title == "Historial de Gastos":
                    st.session_state.gastos_raw_data = original_df_to_update
                    if save_dataframe(st.session_state.gastos_raw_data, GASTOS_FILE):
                        st.session_state.gastos_edited = True
                        st.session_state.gastos_data = get_gastos_df_processed()
                        st.success("Cambios en Historial de Gastos guardados exitosamente.")
            except Exception as e:
                st.error(f"Error al procesar los cambios en la tabla: {e}")

def render_tables_and_download():
    """Renderiza las tablas principales y proporciona opciones de descarga."""
    # Tabla de Registros (Proveedores)
    columns_to_format_proveedores = ["Precio Unitario ($)", "Total ($)", "Monto Deposito", "Saldo diario", "Saldo Acumulado"]
    editable_cols_proveedores = {
        "Fecha": "date",
        "Proveedor": "selectbox_proveedores",
        "Cantidad": "number_int",
        "Peso Salida (kg)": "number",
        "Peso Entrada (kg)": "number",
        "Tipo Documento": "selectbox_documento",
        "Cantidad de gavetas": "number_int",
        "Precio Unitario ($)": "number"
    }
    display_formatted_dataframe(
        st.session_state.data,
        "Tabla de Registros",
        columns_to_format=columns_to_format_proveedores,
        key_suffix="proveedores",
        editable_cols=editable_cols_proveedores
    )

    # Tabla de Depósitos
    columns_to_format_depositos = ["Monto"]
    editable_cols_depositos = {
        "Fecha": "date",
        "Empresa": "selectbox_proveedores",
        "Agencia": "selectbox_agencias",
        "Monto": "number"
    }
    display_formatted_dataframe(
        st.session_state.df,
        "Depósitos Registrados",
        columns_to_format=columns_to_format_depositos,
        key_suffix="depositos",
        editable_cols=editable_cols_depositos
    )

    # Tabla de Notas de Débito
    columns_to_format_notas = ["Descuento", "Descuento posible", "Descuento real"]
    editable_cols_notas = {
        "Fecha": "date",
        "Descuento": "number",
        "Descuento real": "number"
    }
    display_formatted_dataframe(
        st.session_state.notas,
        "Tabla de Notas de Débito",
        columns_to_format=columns_to_format_notas,
        key_suffix="notas_debito",
        editable_cols=editable_cols_notas
    )

    # Opciones de descarga
    st.subheader("📥 Descargar Reportes")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 Descargar Proveedores (Excel)", key="download_proveedores"):
            output = BytesIO()
            st.session_state.data.to_excel(output, index=False, sheet_name="registro de proveedores")
            st.download_button(
                label="📥 Descargar Proveedores",
                data=output.getvalue(),
                file_name="registro_proveedores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    with col2:
        if st.button("📄 Descargar Depósitos (Excel)", key="download_depositos"):
            output = BytesIO()
            st.session_state.df.to_excel(output, index=False, sheet_name="registro de depositos")
            st.download_button(
                label="📥 Descargar Depósitos",
                data=output.getvalue(),
                file_name="registro_depositos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    with col3:
        if st.button("📄 Descargar Notas de Débito (Excel)", key="download_notas"):
            output = BytesIO()
            st.session_state.notas.to_excel(output, index=False, sheet_name="registro de notas de debito")
            st.download_button(
                label="📥 Descargar Notas de Débito",
                data=output.getvalue(),
                file_name="registro_notas_debito.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def render_sales_form():
    """Renderiza el formulario para registrar ventas."""
    st.subheader("🐔 Registrar Venta")
    with st.form(key='form_venta', clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_venta = st.date_input("Fecha", value=date.today(), key="fecha_venta")
            cliente = st.selectbox("Cliente", CLIENTES, key="cliente_venta")
            tipo_ave = st.selectbox("Tipo de Ave", TIPOS_AVE, key="tipo_venta")
        with col2:
            cantidad = st.number_input("Cantidad", min_value=0, step=1, key="cantidad_venta")
            libras = st.number_input("Libras", min_value=0.0, step=0.1, format="%.2f", key="libras_venta")
            descuento = st.number_input("Descuento (Libras)", min_value=0.0, step=0.1, format="%.2f", key="descuento_venta")
        with col3:
            precio = st.number_input("Precio ($/Libra)", min_value=0.0, step=0.01, format="%.2f", key="precio_venta")
            pago_cliente = st.number_input("Pago del Cliente ($)", min_value=0.0, step=0.01, format="%.2f", key="pago_venta")
        libras_netas = calcular_libras_netas(libras, descuento)
        total_cobrar = calcular_total_cobrar(libras_netas, precio)
        saldo = calcular_saldo(total_cobrar, pago_cliente)
        st.write(f"**Libras Netas:** {libras_netas:.2f} lbs")
        st.write(f"**Total a Cobrar:** {formatear_moneda(total_cobrar)}")
        st.write(f"**Saldo Pendiente:** {formatear_moneda(saldo)}")
        submit_venta = st.form_submit_button("➕ Registrar Venta")
        if submit_venta:
            if cantidad <= 0 and libras <= 0:
                st.error("Debe ingresar una cantidad o libras válidas.")
            elif precio <= 0:
                st.error("El precio debe ser mayor que cero.")
            else:
                venta_data = {
                    'fecha': fecha_venta,
                    'cliente': cliente,
                    'tipo': tipo_ave,
                    'cantidad': cantidad,
                    'libras': libras,
                    'descuento': descuento,
                    'libras_netas': libras_netas,
                    'precio': precio,
                    'total_a_cobrar': total_cobrar,
                    'pago_cliente': pago_cliente,
                    'saldo': saldo
                }
                if guardar_venta(venta_data):
                    st.success("Venta registrada exitosamente.")

def render_expenses_form():
    """Renderiza el formulario para registrar gastos."""
    st.subheader("💸 Registrar Gasto")
    with st.form(key='form_gasto', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha_gasto = st.date_input("Fecha", value=date.today(), key="fecha_gasto")
            categoria = st.selectbox("Categoría", CATEGORIAS_GASTO, key="categoria_gasto")
            calculo = st.number_input("Cálculo", min_value=0.0, step=0.01, format="%.2f", key="calculo_gasto")
        with col2:
            descripcion = st.text_input("Descripción", key="descripcion_gasto")
            dinero = st.number_input("Dinero ($)", min_value=0.0, step=0.01, format="%.2f", key="dinero_gasto")
        submit_gasto = st.form_submit_button("➕ Registrar Gasto")
        if submit_gasto:
            if dinero <= 0:
                st.error("El monto del gasto debe ser mayor que cero.")
            elif not descripcion.strip():
                st.error("La descripción no puede estar vacía.")
            else:
                gasto_data = {
                    'fecha': fecha_gasto,
                    'calculo': calculo,
                    'descripcion': descripcion,
                    'gasto': categoria,
                    'dinero': dinero
                }
                if guardar_gasto(gasto_data):
                    st.success("Gasto registrado exitosamente.")

def render_sales_and_expenses_tables():
    """Renderiza las tablas de ventas y gastos con opciones de edición y eliminación."""
    st.subheader("📊 Historial de Ventas")
    columns_to_format_ventas = ["Libras", "Descuento", "Libras_netas", "Precio", "Total_a_cobrar", "Pago_Cliente", "Saldo"]
    editable_cols_ventas = {
        "Fecha": "date",
        "Cliente": "selectbox_clientes",
        "Tipo": "selectbox_tipos_ave",
        "Cantidad": "number_int",
        "Libras": "number",
        "Descuento": "number",
        "Precio": "number",
        "Pago_Cliente": "number"
    }
    if not st.session_state.ventas_data.empty:
        display_formatted_dataframe(
            st.session_state.ventas_data,
            "Historial de Ventas",
            columns_to_format=columns_to_format_ventas,
            key_suffix="ventas",
            editable_cols=editable_cols_ventas
        )
        st.subheader("🗑️ Eliminar Ventas")
        indices_ventas = st.multiselect(
            "Selecciona las ventas a eliminar (basado en Cliente y Fecha)",
            options=st.session_state.ventas_data.index,
            format_func=lambda x: f"{st.session_state.ventas_data.loc[x, 'Cliente']} - {st.session_state.ventas_data.loc[x, 'Fecha']}"
        )
        if st.button("🗑️ Eliminar Ventas Seleccionadas", key="eliminar_ventas"):
            if indices_ventas and st.checkbox("✅ Confirmar eliminación de ventas"):
                if eliminar_ventas_seleccionadas(indices_ventas):
                    st.success("Ventas eliminadas exitosamente.")
            elif indices_ventas:
                st.warning("Por favor, confirma la eliminación.")
        if st.button("📥 Descargar Ventas (CSV)", key="download_ventas"):
            output = BytesIO()
            st.session_state.ventas_raw_data.to_csv(output, index=False)
            st.download_button(
                label="📥 Descargar Ventas",
                data=output.getvalue(),
                file_name="ventas.csv",
                mime="text/csv"
            )
    else:
        st.info("No hay ventas registradas.")

    st.subheader("📊 Historial de Gastos")
    columns_to_format_gastos = ["Calculo", "Dinero"]
    editable_cols_gastos = {
        "Fecha": "date",
        "Calculo": "number",
        "Descripcion": "text",
        "Gasto": "selectbox_categorias_gasto",
        "Dinero": "number"
    }
    if not st.session_state.gastos_data.empty:
        display_formatted_dataframe(
            st.session_state.gastos_data,
            "Historial de Gastos",
            columns_to_format=columns_to_format_gastos,
            key_suffix="gastos",
            editable_cols=editable_cols_gastos
        )
        st.subheader("🗑️ Eliminar Gastos")
        indices_gastos = st.multiselect(
            "Selecciona los gastos a eliminar (basado en Descripción y Fecha)",
            options=st.session_state.gastos_data.index,
            format_func=lambda x: f"{st.session_state.gastos_data.loc[x, 'Descripcion']} - {st.session_state.gastos_data.loc[x, 'Fecha']}"
        )
        if st.button("🗑️ Eliminar Gastos Seleccionados", key="eliminar_gastos"):
            if indices_gastos and st.checkbox("✅ Confirmar eliminación de gastos"):
                if eliminar_gastos_seleccionados(indices_gastos):
                    st.success("Gastos eliminados exitosamente.")
            elif indices_gastos:
                st.warning("Por favor, confirma la eliminación.")
        if st.button("📥 Descargar Gastos (CSV)", key="download_gastos"):
            output = BytesIO()
            st.session_state.gastos_raw_data.to_csv(output, index=False)
            st.download_button(
                label="📥 Descargar Gastos",
                data=output.getvalue(),
                file_name="gastos.csv",
                mime="text/csv"
            )
    else:
        st.info("No hay gastos registrados.")

def render_alerts_section():
    """Renderiza la sección de alertas de clientes."""
    st.subheader("🚨 Alertas de Clientes")
    alertas_df = analizar_alertas_clientes(st.session_state.ventas_data)
    if not alertas_df.empty:
        st.write("**Clientes con saldos pendientes o patrones de deuda:**")
        alertas_df['Saldo_Total'] = alertas_df['Saldo_Total'].apply(formatear_moneda)
        st.dataframe(alertas_df, use_container_width=True)
        if st.button("📥 Descargar Alertas (CSV)", key="download_alertas"):
            output = BytesIO()
            alertas_df.to_csv(output, index=False)
            st.download_button(
                label="📥 Descargar Alertas",
                data=output.getvalue(),
                file_name="alertas_clientes.csv",
                mime="text/csv"
            )
    else:
        st.info("No hay alertas de clientes en este momento.")

def render_charts():
    """Renderiza gráficos de análisis."""
    st.subheader("📈 Análisis Gráfico")
    if not st.session_state.data.empty:
        df_data = st.session_state.data[st.session_state.data["Proveedor"] != "BALANCE_INICIAL"].copy()
        df_data["Fecha"] = pd.to_datetime(df_data["Fecha"], errors="coerce")
        df_data = df_data.dropna(subset=["Fecha"])
        df_data["Mes"] = df_data["Fecha"].dt.to_period("M").dt.to_timestamp()
        saldo_por_mes = df_data.groupby("Mes")["Saldo diario"].sum().reset_index()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(saldo_por_mes["Mes"], saldo_por_mes["Saldo diario"], marker="o")
        ax.set_title("Saldo Diario por Mes")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Saldo Diario ($)")
        ax.grid(True)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %Y"))
        plt.xticks(rotation=45)
        st.pyplot(fig)

    if not st.session_state.ventas_data.empty:
        ventas_por_cliente = st.session_state.ventas_data.groupby("Cliente")["Total_a_cobrar"].sum().reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(ventas_por_cliente["Cliente"], ventas_por_cliente["Total_a_cobrar"])
        ax.set_title("Ventas Totales por Cliente")
        ax.set_xlabel("Cliente")
        ax.set_ylabel("Total a Cobrar ($)")
        plt.xticks(rotation=90)
        st.pyplot(fig)

def render_clear_data_section():
    """Renderiza la sección para limpiar datos."""
    st.subheader("🧹 Limpiar Datos")
    st.warning("¡Cuidado! Estas acciones eliminarán todos los registros permanentemente.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpiar Todas las Ventas", key="clear_ventas"):
            if st.checkbox("✅ Confirmar eliminación de todas las ventas"):
                if limpiar_ventas():
                    st.success("Todas las ventas han sido eliminadas.")
            else:
                st.warning("Por favor, confirma la eliminación.")
    with col2:
        if st.button("🗑️ Limpiar Todos los Gastos", key="clear_gastos"):
            if st.checkbox("✅ Confirmar eliminación de todos los gastos"):
                if limpiar_gastos():
                    st.success("Todos los gastos han sido eliminados.")
            else:
                st.warning("Por favor, confirma la eliminación.")

# --- 6. FLUJO PRINCIPAL DE LA APLICACIÓN ---
def main():
    """Flujo principal de la aplicación."""
    initialize_session_state()
    st.title("🐔 Sistema de Gestión de Proveedores y Ventas - Producto Pollo")

    # Barra lateral para navegación
    st.sidebar.title("🧭 Navegación")
    opcion = st.sidebar.radio(
        "Selecciona una sección",
        [
            "🏠 Inicio",
            "📝 Registro de Proveedores",
            "💰 Depósitos",
            "📋 Notas de Débito",
            "🐔 Ventas y Gastos",
            "📈 Reportes y Gráficos",
            "📁 Importar Datos"
        ],
        key="nav_radio"
    )

    # Barra lateral para registro de depósitos
    if opcion != "💰 Depósitos":
        render_deposit_registration_form()
        render_delete_deposit_section()
        render_edit_deposit_section()

    # Renderizar contenido según la sección seleccionada
    if opcion == "🏠 Inicio":
        st.header("🏠 Bienvenido al Sistema de Gestión")
        st.markdown("""
        Este sistema te permite gestionar proveedores, depósitos, notas de débito, ventas y gastos para el producto **Pollo**. Utiliza la barra lateral para navegar entre las secciones.
        
        ### Resumen Rápido
        - **Proveedores Registrados**: {}
        - **Depósitos Totales**: {}
        - **Ventas Totales**: {}
        - **Gastos Totales**: {}
        """.format(
            len(st.session_state.data[st.session_state.data["Proveedor"] != "BALANCE_INICIAL"]),
            formatear_moneda(st.session_state.df["Monto"].sum() if not st.session_state.df.empty else 0),
            formatear_moneda(st.session_state.ventas_data["Total_a_cobrar"].sum() if not st.session_state.ventas_data.empty else 0),
            formatear_moneda(st.session_state.gastos_data["Dinero"].sum() if not st.session_state.gastos_data.empty else 0)
        ))

    elif opcion == "📝 Registro de Proveedores":
        render_supplier_registration_form()
        render_tables_and_download()

    elif opcion == "💰 Depósitos":
        st.header("💰 Gestión de Depósitos")
        render_deposit_registration_form()
        render_delete_deposit_section()
        render_edit_deposit_section()
        render_tables_and_download()

    elif opcion == "📋 Notas de Débito":
        st.header("📋 Gestión de Notas de Débito")
        render_debit_note_form()
        render_delete_debit_note_section()
        render_edit_debit_note_section()
        render_tables_and_download()

    elif opcion == "🐔 Ventas y Gastos":
        st.header("🐔 Gestión de Ventas y Gastos")
        render_sales_form()
        render_expenses_form()
        render_sales_and_expenses_tables()
        render_alerts_section()
        render_clear_data_section()

    elif opcion == "📈 Reportes y Gráficos":
        st.header("📈 Reportes y Gráficos")
        render_tables_and_download()
        render_charts()

    elif opcion == "📁 Importar Datos":
        st.header("📁 Importar Datos")
        render_import_excel_section()

    # Recalcular saldos si hubo cambios
    if any([
        st.session_state.record_added, st.session_state.record_deleted, st.session_state.record_edited,
        st.session_state.deposit_added, st.session_state.deposit_deleted, st.session_state.deposit_edited,
        st.session_state.debit_note_added, st.session_state.debit_note_deleted, st.session_state.debit_note_edited,
        st.session_state.data_imported
    ]):
        recalculate_accumulated_balances()
        st.session_state.record_added = False
        st.session_state.record_deleted = False
        st.session_state.record_edited = False
        st.session_state.deposit_added = False
        st.session_state.deposit_deleted = False
        st.session_state.deposit_edited = False
        st.session_state.debit_note_added = False
        st.session_state.debit_note_deleted = False
        st.session_state.debit_note_edited = False
        st.session_state.data_imported = False

if __name__ == "__main__":
    main()
