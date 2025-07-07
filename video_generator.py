import subprocess
import os
import json
from pathlib import Path

class VideoGenerator:
    def __init__(self, upload_folder='uploads', output_folder='generated_videos'):
        self.upload_folder = upload_folder
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
    
    def create_property_video(self, files_data, property_data, job_id):
        """
        Cria um vídeo promocional do imóvel usando FFmpeg
        """
        try:
            # Separar imagens e vídeos
            images = [f for f in files_data if f['type'] == 'image']
            videos = [f for f in files_data if f['type'] == 'video']
            
            # Criar vídeo a partir das imagens (slideshow)
            image_video_path = None
            if images:
                image_video_path = self._create_slideshow(images, job_id)
            
            # Processar vídeos existentes
            processed_videos = []
            for video in videos:
                processed_path = self._process_video(video, job_id)
                if processed_path:
                    processed_videos.append(processed_path)
            
            # Combinar todos os vídeos
            all_videos = []
            if image_video_path:
                all_videos.append(image_video_path)
            all_videos.extend(processed_videos)
            
            if not all_videos:
                raise Exception("Nenhum conteúdo de vídeo foi gerado")
            
            # Concatenar vídeos
            final_video_path = self._concatenate_videos(all_videos, job_id)
            
            # Adicionar texto/legendas com informações do imóvel
            final_video_with_text = self._add_property_info(final_video_path, property_data, job_id)
            
            return final_video_with_text
            
        except Exception as e:
            print(f"Erro ao gerar vídeo: {str(e)}")
            return None
    
    def _create_slideshow(self, images, job_id):
        """
        Cria um slideshow a partir das imagens
        """
        try:
            # Criar arquivo de lista de imagens
            image_list_file = f"{self.output_folder}/images_{job_id}.txt"
            with open(image_list_file, 'w') as f:
                for img in images:
                    # Cada imagem fica 3 segundos na tela
                    f.write(f"file '{os.path.abspath(img['path'])}'\n")
                    f.write("duration 3\n")
                # Repetir a última imagem
                if images:
                    f.write(f"file '{os.path.abspath(images[-1]['path'])}'\n")
            
            output_path = f"{self.output_folder}/slideshow_{job_id}.mp4"
            
            # Comando FFmpeg para criar slideshow
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', image_list_file,
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264',
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Limpar arquivo temporário
                os.remove(image_list_file)
                return output_path
            else:
                print(f"Erro FFmpeg slideshow: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Erro ao criar slideshow: {str(e)}")
            return None
    
    def _process_video(self, video_data, job_id):
        """
        Processa um vídeo individual (redimensiona, padroniza)
        """
        try:
            input_path = video_data['path']
            output_path = f"{self.output_folder}/processed_{video_data['id']}_{job_id}.mp4"
            
            # Comando FFmpeg para processar vídeo
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-r', '30',
                '-t', '10',  # Limitar a 10 segundos
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Erro FFmpeg processo: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Erro ao processar vídeo: {str(e)}")
            return None
    
    def _concatenate_videos(self, video_paths, job_id):
        """
        Concatena múltiplos vídeos em um só
        """
        try:
            if len(video_paths) == 1:
                return video_paths[0]
            
            # Criar arquivo de lista para concatenação
            concat_file = f"{self.output_folder}/concat_{job_id}.txt"
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            output_path = f"{self.output_folder}/concatenated_{job_id}.mp4"
            
            # Comando FFmpeg para concatenar
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Limpar arquivo temporário
                os.remove(concat_file)
                return output_path
            else:
                print(f"Erro FFmpeg concatenação: {result.stderr}")
                return video_paths[0]  # Retornar o primeiro vídeo se falhar
                
        except Exception as e:
            print(f"Erro ao concatenar vídeos: {str(e)}")
            return video_paths[0] if video_paths else None
    
    def _add_property_info(self, video_path, property_data, job_id):
        """
        Adiciona informações do imóvel como texto sobreposto
        """
        try:
            output_path = f"{self.output_folder}/final_{job_id}.mp4"
            
            # Criar texto com informações do imóvel
            info_text = f"{property_data['name']}"
            if property_data['area']:
                info_text += f" - {property_data['area']}m²"
            if property_data['price']:
                info_text += f" - R$ {property_data['price']}"
            if property_data['location']:
                info_text += f"\\n{property_data['location']}"
            
            # Comando FFmpeg para adicionar texto
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf', f"drawtext=text='{info_text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=h-text_h-20",
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Erro FFmpeg texto: {result.stderr}")
                return video_path  # Retornar vídeo sem texto se falhar
                
        except Exception as e:
            print(f"Erro ao adicionar texto: {str(e)}")
            return video_path

