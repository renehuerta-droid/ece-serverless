from flask import Flask, render_template_string, request, redirect, url_for, session
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secreto_nacional_salud_cui"

# --- CONFIGURACIÓN ---
LAMBDA_URL = "https://lpj4hf2vhkq57fsysyx276wixa0ehlso.lambda-url.us-east-2.on.aws/"

base_datos = {
    "expedientes": {}, # curp: {nombre, pw, historial: []}
    "usuarios": {
        "admin": {"pw": "123", "rol": "Administrador"},
        "dr_simi": {"pw": "123", "rol": "Medico"},
        "recepcion1": {"pw": "123", "rol": "Recepcionista"}
    }
}

LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema ECE Nacional Serverless</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; }
        .nav { 
            background: #2c3e50; 
            color: white; 
            padding: 1rem 2rem; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .nav-info { display: flex; align-items: center; gap: 20px; }
        .btn-logout { 
            background: #e74c3c; 
            color: white; 
            padding: 8px 16px; 
            text-decoration: none; 
            border-radius: 4px; 
            font-weight: bold;
            transition: background 0.3s;
        }
        .btn-logout:hover { background: #c0392b; }
        .container { max-width: 900px; margin: 30px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .card { border-left: 5px solid #3498db; background: #ebf5fb; padding: 20px; margin: 15px 0; border-radius: 0 8px 8px 0; }
        input, select, textarea { padding: 12px; margin: 8px 0; width: 100%; box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; }
        button { background: #27ae60; color: white; padding: 14px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-size: 1.1em; font-weight: bold; }
        button:hover { background: #219150; }
        table { width: 100%; border-collapse: collapse; margin-top: 25px; }
        th, td { text-align: left; padding: 15px; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="nav">
        <span style="font-size: 1.2em; font-weight: bold;">🏥 ECE NACIONAL SERVERLESS</span>
        {% if 'user' in session %}
        <div class="nav-info">
            <span>👤 <b>{{session['rol']}}</b>: {{session['user']}}</span>
            <a href="/logout" class="btn-logout">CERRAR SESIÓN</a>
        </div>
        {% endif %}
    </div>
    <div class="container">{{ content | safe }}</div>
</body>
</html>
"""
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['user'], request.form['pw']
        if u in base_datos['usuarios'] and base_datos['usuarios'][u]['pw'] == p:
            session['user'], session['rol'] = u, base_datos['usuarios'][u]['rol']
            return redirect('/panel')
        if u in base_datos['expedientes'] and base_datos['expedientes'][u]['pw'] == p:
            session['user'], session['rol'] = u, 'Paciente'
            return redirect('/mi-expediente')
        return redirect('/?error=1')
    return render_template_string(LAYOUT, content="""<h2>Acceso</h2><form method="POST"><input name="user" placeholder="Usuario/CURP"><input type="password" name="pw" placeholder="Contraseña"><button>Entrar</button></form>""")

@app.route('/panel')
def panel():
    if 'user' not in session or session['rol'] == 'Paciente': return redirect('/')
    
    html = f"<h3>Panel de Gestión - {session['rol']}</h3>"
    if session['rol'] in ['Administrador', 'Medico']:
        html += """
        <div class="card">
            <h4>Registrar Nuevo Paciente (Primer Ingreso)</h4>
            <form action="/crear" method="POST">
                <input name="n" placeholder="Nombre" required>
                <input name="ap" placeholder="A. Paterno" required>
                <input name="am" placeholder="A. Materno" required>
                <input name="f" placeholder="Nacimiento (YY-MM-DD)" required>
                <input name="e" placeholder="Estado (MC, DF)" required>
                <input name="pw" placeholder="Contraseña para el paciente" required>
                <button type="submit">Generar CURP y Abrir Expediente</button>
            </form>
        </div>
        """
    
    html += "<h4>Listado de Expedientes</h4><table><tr><th>CURP</th><th>Nombre</th><th>Acciones</th></tr>"
    for curp, d in base_datos['expedientes'].items():
        html += f"<tr><td>{curp}</td><td>{d['nombre']}</td><td><a href='/historial/{curp}'>Ver/Añadir Consulta</a></td></tr>"
    html += "</table>"
    return render_template_string(LAYOUT, content=html)

@app.route('/historial/<curp>', methods=['GET', 'POST'])
def historial(curp):
    if 'user' not in session or session['rol'] == 'Paciente': return redirect('/')
    
    if request.method == 'POST':
        nueva_con = {
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "diag": request.form['diag'],
            "med": request.form['med'],
            "prox": request.form['prox']
        }
        base_datos['expedientes'][curp]['historial'].append(nueva_con)
        return redirect(f'/historial/{curp}')

    paciente = base_datos['expedientes'][curp]
    html = f"<h3>Historial Clínico: {paciente['nombre']}</h3>"
    
    if session['rol'] in ['Administrador', 'Medico']:
        html += f"""
        <div class="card">
            <h4>Nueva Consulta</h4>
            <form method="POST">
                <textarea name="diag" placeholder="Diagnóstico de hoy" required></textarea>
                <input name="med" placeholder="Medicamentos y dosis" required>
                <input name="prox" placeholder="Próxima cita (DD/MM/AAAA)" required>
                <button style="background:#3498db;">Guardar Consulta</button>
            </form>
        </div>
        """
    
    html += "<h4>Consultas Anteriores</h4>"
    for c in reversed(paciente['historial']):
        html += f"<div class='card'><b>Fecha:</b> {c['fecha']}<br><b>Diagnóstico:</b> {c['diag']}<br><b>Tratamiento:</b> {c['med']}<br><b>Próxima:</b> {c['prox']}</div>"
    
    html += "<br><a href='/panel'>← Volver al Panel</a>"
    return render_template_string(LAYOUT, content=html)

@app.route('/mi-expediente')
def mi_expediente():
    if session.get('rol') != 'Paciente': return redirect('/')
    paciente = base_datos['expedientes'][session['user']]
    html = f"<h3>Mi Historial de Salud - {paciente['nombre']}</h3>"
    for c in reversed(paciente['historial']):
        html += f"<div class='card'><b>Consulta:</b> {c['fecha']}<hr><b>Diagnóstico:</b> {c['diag']}<br><b>Indicaciones:</b> {c['med']}<br><b>Cita:</b> {c['prox']}</div>"
    return render_template_string(LAYOUT, content=html)

@app.route('/crear', methods=['POST'])
def crear():
    payload = {"nombre": request.form['n'], "paterno": request.form['ap'], "materno": request.form['am'], "fecha": request.form['f'], "estado": request.form['e']}
    r = requests.post(LAMBDA_URL, json=payload).json()
    curp = r.get('curp_generado', 'ERROR')
    
    base_datos['expedientes'][curp] = {
        "nombre": f"{request.form['n']} {request.form['ap']} {request.form['am']}",
        "pw": request.form['pw'],
        "historial": [] # Iniciamos con historial vacío
    }
    return redirect('/panel')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)