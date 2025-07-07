from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import threading
from advanced_video_generator import AdvancedVideoGenerator
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'imovibe_secret_key_2024'  # Em produção, usar variável de ambiente
CORS(app, supports_credentials=True)  # Permitir cookies para sessões

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'webm'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('generated_videos', exist_ok=True)
os.makedirs('user_data', exist_ok=True)

# Armazenar dados em arquivos JSON (em produção, usar banco de dados)
USERS_FILE = 'user_data/users.json'
USAGE_FILE = 'user_data/usage.json'

# Armazenar status dos jobs em memória
job_status = {}

# Inicializar gerador de vídeo avançado
video_generator = AdvancedVideoGenerator()

def load_users():
    """Carrega dados dos usuários"""
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    """Salva dados dos usuários"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_usage():
    """Carrega dados de uso"""
    try:
        with open(USAGE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_usage(usage):
    """Salva dados de uso"""
    with open(USAGE_FILE, 'w') as f:
        json.dump(usage, f, indent=2)

def get_user_limits(user_id):
    """Retorna os limites do usuário"""
    users = load_users()
    user = users.get(user_id, {})
    
    if user.get('plan') == 'paid':
        return {'videos_per_month': -1, 'plan': 'paid'}  # Ilimitado
    else:
        return {'videos_per_month': 3, 'plan': 'free'}  # Teste gratuito

def check_user_usage(user_id):
    """Verifica o uso atual do usuário"""
    usage = load_usage()
    user_usage = usage.get(user_id, {'videos_generated': 0, 'last_reset': datetime.now().isoformat()})
    
    # Verificar se precisa resetar (novo mês)
    last_reset = datetime.fromisoformat(user_usage['last_reset'])
    if datetime.now() - last_reset > timedelta(days=30):
        user_usage = {'videos_generated': 0, 'last_reset': datetime.now().isoformat()}
        usage[user_id] = user_usage
        save_usage(usage)
    
    return user_usage

def increment_user_usage(user_id):
    """Incrementa o uso do usuário"""
    usage = load_usage()
    user_usage = usage.get(user_id, {'videos_generated': 0, 'last_reset': datetime.now().isoformat()})
    user_usage['videos_generated'] += 1
    usage[user_id] = user_usage
    save_usage(usage)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_video_async(job_id, files_data, property_data, user_id):
    """
    Processa o vídeo em background
    """
    try:
        job_status[job_id] = {'status': 'processing', 'progress': 10, 'message': 'Iniciando processamento...'}
        
        job_status[job_id] = {'status': 'processing', 'progress': 30, 'message': 'Processando mídia...'}
        
        # Gerar vídeo
        video_path = video_generator.create_property_video(files_data, property_data, job_id)
        
        if video_path and os.path.exists(video_path):
            # Incrementar uso do usuário
            increment_user_usage(user_id)
            
            job_status[job_id] = {
                'status': 'completed', 
                'progress': 100, 
                'message': 'Vídeo gerado com sucesso!',
                'video_path': video_path,
                'user_id': user_id
            }
        else:
            job_status[job_id] = {
                'status': 'failed', 
                'progress': 0, 
                'message': 'Erro ao gerar vídeo'
            }
            
    except Exception as e:
        job_status[job_id] = {
            'status': 'failed', 
            'progress': 0, 
            'message': f'Erro: {str(e)}'
        }

@app.route('/')
def hello_world():
    return jsonify({'message': 'ImoVibe Video Backend API'})

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de usuário"""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name')
        
        if not email or not name:
            return jsonify({'error': 'Email e nome são obrigatórios'}), 400
        
        users = load_users()
        
        if email in users:
            return jsonify({'error': 'Usuário já existe'}), 400
        
        user_id = str(uuid.uuid4())
        users[email] = {
            'id': user_id,
            'name': name,
            'email': email,
            'plan': 'free',
            'created_at': datetime.now().isoformat()
        }
        
        save_users(users)
        
        # Criar sessão
        session['user_id'] = user_id
        session['email'] = email
        
        return jsonify({
            'message': 'Usuário registrado com sucesso',
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'plan': 'free'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuário"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        users = load_users()
        
        if email not in users:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        user = users[email]
        
        # Criar sessão
        session['user_id'] = user['id']
        session['email'] = email
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'plan': user['plan']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout de usuário"""
    session.clear()
    return jsonify({'message': 'Logout realizado com sucesso'})

@app.route('/api/auth/me')
def get_current_user():
    """Retorna dados do usuário atual"""
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    users = load_users()
    email = session['email']
    
    if email not in users:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    user = users[email]
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'plan': user['plan']
        }
    })

@app.route('/api/dashboard')
def get_dashboard():
    """Retorna dados do dashboard do usuário"""
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    user_id = session['user_id']
    
    # Obter limites e uso
    limits = get_user_limits(user_id)
    usage = check_user_usage(user_id)
    
    # Calcular estatísticas
    videos_generated = usage['videos_generated']
    videos_remaining = limits['videos_per_month'] - videos_generated if limits['videos_per_month'] > 0 else -1
    
    return jsonify({
        'usage': {
            'videos_generated': videos_generated,
            'videos_remaining': videos_remaining,
            'plan': limits['plan'],
            'last_reset': usage['last_reset']
        },
        'limits': limits
    })

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        # Verificar autenticação
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        user_id = session['user_id']
        
        # Verificar limites
        limits = get_user_limits(user_id)
        usage = check_user_usage(user_id)
        
        if limits['videos_per_month'] > 0 and usage['videos_generated'] >= limits['videos_per_month']:
            return jsonify({'error': 'Limite de vídeos atingido. Faça upgrade para o plano pago.'}), 403
        
        # Verificar se há arquivos na requisição
        if 'files' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        files = request.files.getlist('files')
        property_data = {
            'name': request.form.get('name', ''),
            'area': request.form.get('area', ''),
            'price': request.form.get('price', ''),
            'location': request.form.get('location', ''),
            'template': request.form.get('template', ''),
            'music': request.form.get('music', '')
        }
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            if file and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                file_id = str(uuid.uuid4())
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{file_id}.{file_extension}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                uploaded_files.append({
                    'id': file_id,
                    'original_name': filename,
                    'filename': unique_filename,
                    'path': file_path,
                    'type': 'image' if file_extension in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
                })
            else:
                return jsonify({'error': f'Tipo de arquivo não permitido: {file.filename}'}), 400
        
        # Iniciar processamento do vídeo em background
        job_id = str(uuid.uuid4())
        thread = threading.Thread(target=process_video_async, args=(job_id, uploaded_files, property_data, user_id))
        thread.start()
        
        return jsonify({
            'message': 'Upload realizado com sucesso, processamento iniciado',
            'job_id': job_id,
            'property_data': property_data,
            'uploaded_files': len(uploaded_files),
            'status': 'processing'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-status/<job_id>')
def video_status(job_id):
    """
    Endpoint para verificar status do processamento do vídeo
    """
    if job_id not in job_status:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    status_data = job_status[job_id].copy()
    
    # Adicionar URL de download se vídeo estiver pronto
    if status_data['status'] == 'completed' and 'video_path' in status_data:
        status_data['download_url'] = f'/api/download/{job_id}'
        # Remover path interno
        del status_data['video_path']
    
    status_data['job_id'] = job_id
    return jsonify(status_data)

@app.route('/api/download/<job_id>')
def download_video(job_id):
    """
    Endpoint para download do vídeo gerado
    """
    if job_id not in job_status:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    status_data = job_status[job_id]
    
    if status_data['status'] != 'completed' or 'video_path' not in status_data:
        return jsonify({'error': 'Vídeo não está pronto'}), 400
    
    video_path = status_data['video_path']
    
    if not os.path.exists(video_path):
        return jsonify({'error': 'Arquivo de vídeo não encontrado'}), 404
    
    return send_file(video_path, as_attachment=True, download_name=f'imovibe_video_{job_id}.mp4')

@app.route('/api/templates')
def get_templates():
    """
    Endpoint para obter informações sobre templates disponíveis
    """
    return jsonify({
        'templates': video_generator.get_template_info(),
        'music': video_generator.get_music_info()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

