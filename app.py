from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
import threading
from advanced_video_generator import AdvancedVideoGenerator

app = Flask(__name__)
CORS(app)  # Permitir requisições do frontend

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'webm'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('generated_videos', exist_ok=True)

# Armazenar status dos jobs em memória (em produção, usar Redis ou banco de dados)
job_status = {}

# Inicializar gerador de vídeo avançado
video_generator = AdvancedVideoGenerator()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_video_async(job_id, files_data, property_data):
    """
    Processa o vídeo em background
    """
    try:
        job_status[job_id] = {'status': 'processing', 'progress': 10, 'message': 'Iniciando processamento...'}
        
        job_status[job_id] = {'status': 'processing', 'progress': 30, 'message': 'Processando mídia...'}
        
        # Gerar vídeo
        video_path = video_generator.create_property_video(files_data, property_data, job_id)
        
        if video_path and os.path.exists(video_path):
            job_status[job_id] = {
                'status': 'completed', 
                'progress': 100, 
                'message': 'Vídeo gerado com sucesso!',
                'video_path': video_path
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

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
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
        thread = threading.Thread(target=process_video_async, args=(job_id, uploaded_files, property_data))
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

