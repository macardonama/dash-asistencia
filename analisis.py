
import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Conexión a MongoDB Atlas
uri = st.secrets["mongo_uri"]
client = MongoClient(uri)
db = client["asistencia"]
collection = db["asistencias"]

# Leer los datos
data = list(collection.find())
df = pd.DataFrame(data)

# Convertir fechas si existe 'createdAt'
if 'createdAt' in df.columns:
    df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')

# Función para generar PDF por estudiante
def generar_pdf_estudiante(nombre, registros):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Reporte de Asistencia - {nombre}")
    
    y = 720
    for i, row in registros.iterrows():
        fecha = row['createdAt'].strftime("%Y-%m-%d") if pd.notnull(row['createdAt']) else "Sin fecha"
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

# --- Streamlit UI ---
st.title("📊 Dashboard de Asistencia Escolar")

# Filtros por grupo y fecha
grupos_disponibles = sorted(df['grupo'].dropna().unique().tolist())
grupos_disponibles.insert(0, "Todos los grupos")

grupo = st.selectbox("Selecciona un grupo", grupos_disponibles)

min_date = df['createdAt'].min().date()
max_date = df['createdAt'].max().date()

fecha_inicio, fecha_fin = st.date_input(
    "Selecciona el rango de fechas:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Aplicar filtros
if grupo == "Todos los grupos":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['grupo'] == grupo]

df_filtrado = df_filtrado[
    (df_filtrado['createdAt'].dt.date >= fecha_inicio) &
    (df_filtrado['createdAt'].dt.date <= fecha_fin)
]

if df_filtrado.empty:
    st.warning("⚠️ No hay datos disponibles para los filtros seleccionados.")
else:
    # Estadísticas de emociones
    st.subheader("📋 Estadísticas de emociones")
    frecuencia_abs = df_filtrado['emoji'].value_counts()
    frecuencia_rel = df_filtrado['emoji'].value_counts(normalize=True) * 100
    tabla_emociones = pd.concat([frecuencia_abs, frecuencia_rel.round(2)], axis=1)
    tabla_emociones.columns = ['Frecuencia', 'Porcentaje (%)']
    st.dataframe(tabla_emociones)

    if not df_filtrado['emoji'].empty:
        moda = df_filtrado['emoji'].mode()[0]
        st.success(f"😃 Emoción más común: **{moda}**")

    # Resumen general
    st.subheader(f"Resumen para el grupo {grupo}")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total registros", len(df_filtrado))
    with col2:
        st.metric("Estudiantes únicos", df_filtrado['name'].nunique())

    # Gráfico de emociones (pie chart)
    st.subheader("Distribución de emociones")
    emociones = df_filtrado['emoji'].value_counts()
    fig, ax = plt.subplots(facecolor='none')  # sin fondo blanco
    fig.patch.set_facecolor('none')  # fondo transparente
    ax.set_facecolor('none')

    # Colores personalizados (puedes cambiarlos si quieres)
    colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0','#ffb3e6']

    ax.pie(
        emociones,
        labels=emociones.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        textprops={'color': 'white', 'fontsize': 12}
    )

    ax.axis('equal')  # mantiene el círculo
    st.pyplot(fig)
    # Gráfico de estado (Presente/Ausente)
    if 'estado' in df_filtrado.columns:
        st.subheader("Estado de asistencia")
        estado = df_filtrado['estado'].value_counts()
        st.bar_chart(estado)

    # Exportar datos
    st.subheader("📦 Exportar datos")

    # Descargar Excel
    buffer = io.BytesIO()
    df_filtrado.to_excel(buffer, index=False, sheet_name="Asistencia")
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar Excel",
        data=buffer,
        file_name=f"asistencia_{grupo}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Generar PDF por estudiante
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
