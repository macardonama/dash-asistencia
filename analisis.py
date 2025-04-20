import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# Conexión a MongoDB Atlas
#uri = "mongodb+srv://macardonama:FCvRAwuxbT2vQrcO@cluster0.yeqavsk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
uri=uri = st.secrets["mongo_uri"]
client = MongoClient(uri)
db = client["asistencia"]
collection = db["asistencias"]

# Leer los datos
data = list(collection.find())
df = pd.DataFrame(data)

def generar_pdf_estudiante(nombre, registros):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Reporte de Asistencia - {nombre}")
    
    y = 720
    for i, row in registros.iterrows():
        fecha = row['createdAt'].strftime("%Y-%m-%d")
        estado = row.get('estado', 'N/A')
        emocion = row.get('emoji', 'N/A')
        c.drawString(50, y, f"{fecha}: Estado = {estado}, Emoción = {emocion}")
        y -= 20
        if y < 100:
            c.showPage()
            y = 750
    
    c.save()
    buffer.seek(0)
    return buffer


# Convertir fechas si existe 'createdAt'
if 'createdAt' in df.columns:
    df['createdAt'] = pd.to_datetime(df['createdAt'])

# --- Streamlit UI ---
st.title("📊 Dashboard de Asistencia Escolar")

# Filtros
#grupo = st.selectbox("Selecciona un grupo", sorted(df['grupo'].unique()))
#df_filtrado = df[df['grupo'] == grupo]
#Nuevo Filtrado para aceptar Todos
grupos_disponibles = sorted(df['grupo'].dropna().unique().tolist())
grupos_disponibles.insert(0, "Todos los grupos")  # Insertar opción global al inicio

grupo = st.selectbox("Selecciona un grupo", grupos_disponibles)
if grupo == "Todos los grupos":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['grupo'] == grupo]
#Aca finaliza nuevo codigo

st.subheader("🗓️ Filtrar por fecha")

# Definir fechas mínima y máxima en los datos
min_date = df['createdAt'].min().date()
max_date = df['createdAt'].max().date()

# Selector de rango de fechas
fecha_inicio, fecha_fin = st.date_input(
    "Selecciona el rango de fechas:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filtrar por fecha seleccionada
df_filtrado = df[
    (df['grupo'] == grupo) &
    (df['createdAt'].dt.date >= fecha_inicio) &
    (df['createdAt'].dt.date <= fecha_fin)
]

st.subheader("📋 Estadísticas de emociones")

# Calcular frecuencia absoluta y relativa
frecuencia_abs = df_filtrado['emoji'].value_counts()
frecuencia_rel = df_filtrado['emoji'].value_counts(normalize=True) * 100

# Combinar en una tabla
tabla_emociones = pd.concat([frecuencia_abs, frecuencia_rel.round(2)], axis=1)
tabla_emociones.columns = ['Frecuencia', 'Porcentaje (%)']

# Mostrar tabla
st.dataframe(tabla_emociones)

# Calcular y mostrar la moda
if not df_filtrado['emoji'].empty:
    moda = df_filtrado['emoji'].mode()[0]
    st.success(f"😃 Emoción más común: **{moda}**")
else:
    st.warning("No hay emociones registradas en este rango.")

# Mostrar resumen
st.subheader(f"Resumen para el grupo {grupo}")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total registros", len(df_filtrado))
with col2:
    st.metric("Estudiantes únicos", df_filtrado['name'].nunique())

# Gráfico de emociones
st.subheader("Frecuencia de emociones")
emociones = df_filtrado['emoji'].value_counts()
fig, ax = plt.subplots()
emociones.plot(kind='bar', ax=ax, color='skyblue')
plt.xlabel("Emoción")
plt.ylabel("Frecuencia")
st.pyplot(fig)


# Gráfico de estado (Presente/Ausente)
if 'estado' in df_filtrado.columns:
    st.subheader("Estado de asistencia")
    estado = df_filtrado['estado'].value_counts()
    st.bar_chart(estado)

st.subheader("📥 Descargar datos en Excel")

st.subheader("📄 Generar reporte individual en PDF")

estudiantes = sorted(df_filtrado['name'].dropna().unique())
estudiante_seleccionado = st.selectbox("Selecciona un estudiante", estudiantes)

if st.button("Generar PDF"):
    registros_estudiante = df_filtrado[df_filtrado['name'] == estudiante_seleccionado]
    pdf_buffer = generar_pdf_estudiante(estudiante_seleccionado, registros_estudiante)
    
    st.download_button(
        label="📥 Descargar PDF",
        data=pdf_buffer,
        file_name=f"reporte_{estudiante_seleccionado}.pdf",
        mime="application/pdf"
    )


# Crear buffer para Excel
buffer = io.BytesIO()
df_filtrado.to_excel(buffer, index=False, sheet_name="Asistencia")
buffer.seek(0)

# Botón de descarga
st.download_button(
    label="📥 Descargar Excel",
    data=buffer,
    file_name=f"asistencia_{grupo}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)